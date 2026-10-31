"""Focused geometry, source-art and hardware checks for Phase 1.4."""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/oberreut"))


def _map(path):
    return np.frombuffer(path.read_bytes(), dtype="<u2").reshape(64, 64)


def test_tree_ring_paving_and_stop_keep_all_physics(tmp_path):
    from phase14 import AXIS_ROWS, TILE_IDS, TREE_ORIGINS, generate

    report = generate(ROOT, tmp_path)
    before = _map(ROOT / "data/oberreut/phase13-derived/Oberreut/map.bin")
    after = _map(tmp_path / "Oberreut/map.bin")
    assert np.array_equal(before & 0xFC00, after & 0xFC00)
    assert report["changed_collision_cells"] == 0
    assert len(report["tree_origins"]) == len(set(map(tuple, report["tree_origins"]))) == 12
    symbols = ((0, 0, "tree_nw"), (1, 0, "tree_ne"), (0, 1, "tree_sw"), (1, 1, "tree_se"))
    for x, y in TREE_ORIGINS:
        for dx, dy, symbol in symbols:
            assert (after[y + dy, x + dx] & 1023) == TILE_IDS[symbol]
    for y in AXIS_ROWS:
        assert sum((after[y, x] & 1023) == TILE_IDS["paver_axis"] for x in range(18, 42)) >= 20
    assert (after[20, 45] & 1023) == TILE_IDS["stop_sign"]
    assert (after[27, 50] & 1023) == TILE_IDS["shelter"]
    assert (tmp_path / "OberreutOst/map.bin").read_bytes() == (ROOT / "data/oberreut/phase13-derived/OberreutOst/map.bin").read_bytes()


def test_two_tracks_staggered_platforms_and_waiting_areas(tmp_path):
    from phase14 import TILE_IDS, generate

    report = generate(ROOT, tmp_path)
    after = _map(tmp_path / "Oberreut/map.bin")
    for y in range(12, 40):
        assert (after[y, 46] & 1023) == TILE_IDS["rail"]
        assert (after[y, 47] & 1023) == TILE_IDS["ballast"]
        assert (after[y, 48] & 1023) == TILE_IDS["rail"]
    assert {entry["osm_way"] for entry in report["platform_cells"]} == {35995211, 35995212}
    assert all((after[y, x] & 1023) in (TILE_IDS["platform_left"], TILE_IDS["platform_right"],
                                       TILE_IDS["stop_sign"])
               for x, y in [entry["xy"] for entry in report["platform_cells"]])
    assert all((after[y, x] & 1023) in (TILE_IDS["waiting"], TILE_IDS["shelter"])
               for x, y in report["waiting_cells"])


def test_explicit_pixel_source_and_generated_bytes_are_repeatable(tmp_path):
    from phase14 import ART_SOURCE, TILE_IDS, generate

    source = json.loads((ROOT / ART_SOURCE).read_text())
    assert source["format"] == "indexed-pixel-source-v1"
    assert source["images"]["tree"] and len(source["images"]["tree"]) == 32
    assert "ImageDraw" not in (ROOT / "tools/oberreut/phase14.py").read_text()
    generate(ROOT, tmp_path / "a")
    generate(ROOT, tmp_path / "b")
    files = [p.relative_to(tmp_path / "a") for p in (tmp_path / "a").rglob("*") if p.is_file()]
    assert all((tmp_path / "a" / p).read_bytes() == (tmp_path / "b" / p).read_bytes() for p in files)
    atlas = Image.open(tmp_path / "a/tiles.png")
    assert atlas.mode == "P" and atlas.width * atlas.height // 64 <= 512
    assert np.asarray(atlas).max() < 16
    raw = (tmp_path / "a/metatiles.bin").read_bytes()
    assert len(raw) == (max(TILE_IDS.values()) - 511) * 16
    for ident in TILE_IDS.values():
        values = struct.unpack_from("<8H", raw, (ident - 512) * 16)
        assert all(value >> 12 == 6 for value in values[:4])
        assert values[4:] == (0, 0, 0, 0)


def test_installed_phase14_assets_match_generated_output():
    for name in ("Oberreut", "OberreutOst"):
        assert (ROOT / f"data/layouts/{name}/map.bin").read_bytes() == (ROOT / f"data/oberreut/phase14-derived/{name}/map.bin").read_bytes()
    for name in ("tiles.png", "metatiles.bin", "metatile_attributes.bin"):
        assert (ROOT / f"data/tilesets/secondary/oberreut/{name}").read_bytes() == (ROOT / f"data/oberreut/phase14-derived/{name}").read_bytes()
