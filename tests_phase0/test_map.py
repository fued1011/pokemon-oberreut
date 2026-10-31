import hashlib
import json
import struct
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/oberreut"))


def test_generated_native_layout_matches_gis_collision_and_spawn(tmp_path):
    from generate_map import generate

    generate(ROOT, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["source_sha256"] == {
        "osm.json": "f5a9fd6e9ec27865b10f73b64d125379f4181cd2112a0d6962d6bc1b1f235150",
        "boundary.geojson": "2042247c7913d06516c042fd644ec042548227e3a33d2fde3fed4ad00ed49eb2",
    }
    data = (tmp_path / "map.bin").read_bytes()
    tiles = struct.unpack("<4096H", data)
    assert len(data) == 8192
    assert manifest["crop"] == [64, 160, 64, 64]
    assert manifest["spawn"] == [30, 28]
    source = json.loads((ROOT / "data/oberreut/chunks/0_1.json").read_text())
    for x, y in [(94, 188), (68, 162), (100, 200), (125, 220)]:
        source_index = (y - 128) * 128 + x
        gba_index = (y - 160) * 64 + x - 64
        assert bool(tiles[gba_index] & 0xC00) == bool(source["blocked"][source_index]) or x in (64, 127) or y in (160, 223)
    assert tiles[28 * 64 + 30] & 0xC00 == 0
    assert manifest["blocked_cells"] > 100
    assert manifest["terrain_counts"]["building"] > 100
    # Category colours must be visibly distinct, not water/grass tiles on streets.
    assert tiles[28 * 64 + 30] & 0x3FF == 435
    assert any(v & 0x3FF == 521 and v & 0xC00 for v in tiles)
    assert any(v & 0x3FF == 533 and not v & 0xC00 for v in tiles)
    for y in range(64):
        for x in range(64):
            original = (y + 32) * 128 + x + 64
            on_border = x in (0, 63) or y in (0, 63)
            assert bool(tiles[y * 64 + x] & 0xC00) == (bool(source["blocked"][original]) or on_border)
            assert tiles[y * 64 + x] & 0xF000 == 0x3000


def test_rejects_gis_snapshot_tampering(tmp_path):
    from generate_map import generate

    source = tmp_path / "root/data/oberreut"
    source.mkdir(parents=True)
    (source / "osm.json").write_bytes((ROOT / "data/oberreut/osm.json").read_bytes())
    (source / "boundary.geojson").write_text("tampered")
    with pytest.raises(ValueError, match="GIS snapshot changed: boundary.geojson"):
        generate(tmp_path / "root", tmp_path / "out")


def test_native_map_is_registered_with_start_warp_and_save_path():
    maps = json.loads((ROOT / "data/maps/map_groups.json").read_text())
    layouts = json.loads((ROOT / "data/layouts/layouts.json").read_text())
    map_json = json.loads((ROOT / "data/maps/Oberreut/map.json").read_text())
    assert "Oberreut" in maps["gMapGroup_TownsAndRoutes"]
    assert any(l["id"] == "LAYOUT_OBERREUT" and l["width"] == 64 and l["height"] == 64 for l in layouts["layouts"])
    assert map_json["layout"] == "LAYOUT_OBERREUT"
    assert map_json["object_events"] == map_json["warp_events"] == map_json["coord_events"] == []
    new_game = (ROOT / "src/new_game.c").read_text()
    assert "SetWarpDestination(MAP_GROUP(MAP_OBERREUT), MAP_NUM(MAP_OBERREUT), WARP_ID_NONE, 30, 28)" in new_game
    assert "WarpIntoMap();" in new_game
    assert "AddStartMenuAction(MENU_ACTION_SAVE)" in (ROOT / "src/start_menu.c").read_text()


def test_generator_is_reproducible_and_rejects_modified_gis(tmp_path):
    from generate_map import generate

    a, b = tmp_path / "a", tmp_path / "b"
    generate(ROOT, a)
    generate(ROOT, b)
    assert (a / "map.bin").read_bytes() == (b / "map.bin").read_bytes()
    assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()
    # Historical phase-0 generator stays reproducible; live west layout now opens
    # onto the independently generated connected eastern map.
    assert (a / "map.bin").stat().st_size == 8192
    assert hashlib.sha256((ROOT / "data/oberreut/osm.json").read_bytes()).hexdigest() == json.loads((a / "manifest.json").read_text())["source_sha256"]["osm.json"]
