"""Targeted collision and reachability checks for Phase 1.5a.1."""
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/oberreut"))


def _map(path):
    return np.frombuffer(path.read_bytes(), dtype="<u2").reshape(64, 64)


def _reachable(cells, start=(30, 28)):
    pending, seen = deque([start]), {start}
    while pending:
        x, y = pending.popleft()
        for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            px, py = point
            if (0 <= px < 64 and 0 <= py < 64 and point not in seen
                    and not (int(cells[py, px]) & 0x0C00)):
                seen.add(point)
                pending.append(point)
    return seen


def test_only_proven_visual_collision_conflicts_are_fixed(tmp_path):
    from phase15a1 import FACADE_WALL_CELLS, HEDGE_CELLS, TREE_TRUNK_CELLS, generate

    report = generate(ROOT, tmp_path)
    before = _map(ROOT / "data/oberreut/phase15a-derived/Oberreut/map.bin")
    after = _map(tmp_path / "Oberreut/map.bin")
    expected = set(TREE_TRUNK_CELLS) | {(39, 16)}
    changed = {(int(x), int(y)) for y, x in np.argwhere(before != after)}
    assert changed == expected
    assert report["changed_collision_cells"] == 25
    assert len(report["tree_trunk_conflicts_before"]) == 24
    assert report["facade_wall_conflicts_before"] == []
    assert report["hedge_conflicts_before"] == [[39, 16]]
    assert np.array_equal(before & 0xF3FF, after & 0xF3FF)
    assert all(after[y, x] & 0x0C00 for x, y in TREE_TRUNK_CELLS)
    assert all(after[y, x] & 0x0C00 for x, y in FACADE_WALL_CELLS)
    assert all(after[y, x] & 0x0C00 for x, y in HEDGE_CELLS)


def test_no_required_access_or_walkable_cell_is_disconnected(tmp_path):
    from phase15a1 import TREE_TRUNK_CELLS, generate

    generate(ROOT, tmp_path)
    before = _map(ROOT / "data/oberreut/phase15a-derived/Oberreut/map.bin")
    after = _map(tmp_path / "Oberreut/map.bin")
    old, new = _reachable(before), _reachable(after)
    intended = set(TREE_TRUNK_CELLS) | {(39, 16)}
    assert new == old - intended
    assert (30, 17) in new  # normal facade viewing position
    assert (34, 28) in new  # adjacent to the existing NPC at 35,28
    assert any((63, y) in new for y in range(64))  # east-map connection
    assert (30, 28) in new


def test_all_nonmap_assets_and_east_map_are_preserved(tmp_path):
    from phase15a1 import generate

    generate(ROOT, tmp_path)
    source = ROOT / "data/oberreut/phase15a-derived"
    assert (tmp_path / "OberreutOst/map.bin").read_bytes() == (source / "OberreutOst/map.bin").read_bytes()
    for name in ("tiles.png", "metatiles.bin", "metatile_attributes.bin"):
        assert (tmp_path / name).read_bytes() == (source / name).read_bytes()
    for palette in (source / "palettes").glob("*.pal"):
        assert (tmp_path / "palettes" / palette.name).read_bytes() == palette.read_bytes()


def test_installed_phase15a1_assets_match_generated_output():
    derived = ROOT / "data/oberreut/phase15a1-derived"
    for name in ("Oberreut", "OberreutOst"):
        assert (ROOT / f"data/layouts/{name}/map.bin").read_bytes() == (derived / name / "map.bin").read_bytes()
    for name in ("tiles.png", "metatiles.bin", "metatile_attributes.bin"):
        assert (ROOT / f"data/tilesets/secondary/oberreut/{name}").read_bytes() == (derived / name).read_bytes()
