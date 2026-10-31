"""Focused map, art-budget and preservation checks for Phase 1.5a."""
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


def test_north_block_has_four_storeys_stairwells_and_entrances(tmp_path):
    from phase15a import ENTRANCES, HEDGES, SLOT_IDS, STAIRWELLS, generate

    report = generate(ROOT, tmp_path)
    before = _map(ROOT / "data/oberreut/phase14-derived/Oberreut/map.bin")
    after = _map(tmp_path / "Oberreut/map.bin")
    assert np.array_equal(before & 0xFC00, after & 0xFC00)
    assert report["changed_collision_cells"] == 0
    assert report["visible_storey_rows"] == [13, 14, 15, 16]
    for y in range(13, 17):
        for x in STAIRWELLS:
            assert (after[y, x] & 1023) == SLOT_IDS["facade_stair"]
    for x in ENTRANCES:
        assert (after[16, x] & 1023) == SLOT_IDS["entrance"]
    for x in HEDGES:
        assert (after[16, x] & 1023) == SLOT_IDS["hedge"]


def test_only_north_block_changes_and_phase14_scene_is_preserved(tmp_path):
    from phase14 import TILE_IDS, TREE_ORIGINS
    from phase15a import HEDGES, generate

    generate(ROOT, tmp_path)
    before = _map(ROOT / "data/oberreut/phase14-derived/Oberreut/map.bin")
    after = _map(tmp_path / "Oberreut/map.bin")
    allowed = {(x, y) for y in (10, 11, 12) for x in range(22, 39)}
    allowed |= {(x, y) for y in (13, 14, 15, 16) for x in range(21, 39)}
    allowed |= {(x, 16) for x in HEDGES}
    changed = {(int(x), int(y)) for y, x in np.argwhere(before != after)}
    assert changed <= allowed
    symbols = ((0, 0, "tree_nw"), (1, 0, "tree_ne"),
               (0, 1, "tree_sw"), (1, 1, "tree_se"))
    for x, y in TREE_ORIGINS:
        for dx, dy, kind in symbols:
            assert (after[y + dy, x + dx] & 1023) == TILE_IDS[kind]
    assert (tmp_path / "OberreutOst/map.bin").read_bytes() == (
        ROOT / "data/oberreut/phase14-derived/OberreutOst/map.bin").read_bytes()


def test_reuses_unique_tiles_with_fixed_480_tile_budget(tmp_path):
    from phase15a import ART_SOURCE, SLOT_IDS, generate

    report = generate(ROOT, tmp_path)
    source = ROOT / "data/oberreut/phase14-derived"
    atlas_before = Image.open(source / "tiles.png")
    atlas_after = Image.open(tmp_path / "tiles.png")
    assert atlas_after.size == atlas_before.size
    assert atlas_after.width * atlas_after.height // 64 == 480
    assert report["secondary_hardware_tiles_before"] == 480
    assert report["secondary_hardware_tiles_after"] == 480
    assert (tmp_path / "metatiles.bin").read_bytes() == (source / "metatiles.bin").read_bytes()
    assert (tmp_path / "metatile_attributes.bin").read_bytes() == (source / "metatile_attributes.bin").read_bytes()
    raw = (source / "metatiles.bin").read_bytes()
    changed_pixels = np.argwhere(np.asarray(atlas_before) != np.asarray(atlas_after))
    allowed = set()
    for ident in SLOT_IDS.values():
        values = struct.unpack_from("<8H", raw, (ident - 512) * 16)
        for tile in (value & 1023 for value in values[:4]):
            relative = tile - 512
            x0, y0 = (relative % 16) * 8, (relative // 16) * 8
            allowed.update((y, x) for y in range(y0, y0 + 8) for x in range(x0, x0 + 8))
    assert {(int(y), int(x)) for y, x in changed_pixels} <= allowed
    source_art = json.loads((ROOT / ART_SOURCE).read_text())
    assert source_art["format"] == "indexed-pixel-source-v1"
    assert set(SLOT_IDS) <= set(source_art["images"])
    assert "ImageDraw" not in (ROOT / "tools/oberreut/phase15a.py").read_text()


def test_walkable_tree_trunks_are_documented_without_collision_change(tmp_path):
    from phase14 import TREE_ORIGINS
    from phase15a import generate

    report = generate(ROOT, tmp_path)
    after = _map(tmp_path / "Oberreut/map.bin")
    assert report["tree_trunks_walkable"] is True
    assert "documented only" in report["tree_collision_note"]
    assert all((after[y + 1, x] & 0x0C00) == 0 for x, y in TREE_ORIGINS)


def test_installed_phase15a_assets_match_generated_output():
    derived = ROOT / "data/oberreut/phase15a-derived"
    for name in ("Oberreut", "OberreutOst"):
        assert (ROOT / f"data/layouts/{name}/map.bin").read_bytes() == (derived / name / "map.bin").read_bytes()
    for name in ("tiles.png", "metatiles.bin", "metatile_attributes.bin"):
        assert (ROOT / f"data/tilesets/secondary/oberreut/{name}").read_bytes() == (derived / name).read_bytes()
