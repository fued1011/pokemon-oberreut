#!/usr/bin/env python3
"""Phase 1.5a.1: align tree, hedge and facade visuals with collision."""
import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np

import phase14
import phase15a as base

TREE_TRUNK_CELLS = tuple(
    (x + dx, y + 1) for x, y in phase14.TREE_ORIGINS for dx in (0, 1)
)
FACADE_WALL_CELLS = tuple((x, 16) for x in range(21, 39))
HEDGE_CELLS = tuple((x, 16) for x in sorted(base.HEDGES))
SPAWN = (30, 28)


def _map(path):
    return np.frombuffer(path.read_bytes(), dtype="<u2").reshape(64, 64)


def _reachable(cells, start=SPAWN):
    pending = deque([start])
    seen = {start}
    while pending:
        x, y = pending.popleft()
        for point in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            px, py = point
            if (0 <= px < 64 and 0 <= py < 64 and point not in seen
                    and not (int(cells[py, px]) & 0x0C00)):
                seen.add(point)
                pending.append(point)
    return seen


def generate(root, output):
    root = Path(root)
    output = Path(output)
    report = base.generate(root, output)
    west_path = output / "Oberreut/map.bin"
    before = _map(west_path).copy()
    after = before.copy()

    tree_conflicts = [point for point in TREE_TRUNK_CELLS
                      if not (int(before[point[1], point[0]]) & 0x0C00)]
    facade_conflicts = [point for point in FACADE_WALL_CELLS
                        if not (int(before[point[1], point[0]]) & 0x0C00)]
    hedge_conflicts = [point for point in HEDGE_CELLS
                       if not (int(before[point[1], point[0]]) & 0x0C00)]

    # The bottom half of every 2x2 tree contains its visible trunk. Canopy
    # cells remain walkable so the player can still pass visually behind it.
    fixes = tuple(tree_conflicts + facade_conflicts + hedge_conflicts)
    for x, y in fixes:
        after[y, x] = int(after[y, x]) | 0x0C00

    # Tile IDs and elevation remain byte-for-byte equivalent; only collision
    # bits of proven visual obstacles may change.
    assert np.array_equal(after & 0xF3FF, before & 0xF3FF)
    changed = {(int(x), int(y)) for y, x in np.argwhere(after != before)}
    assert changed == set(fixes)
    assert all(int(after[y, x]) & 0x0C00 for x, y in TREE_TRUNK_CELLS)
    assert all(int(after[y, x]) & 0x0C00 for x, y in FACADE_WALL_CELLS)
    assert all(int(after[y, x]) & 0x0C00 for x, y in HEDGE_CELLS)

    before_reachable = _reachable(before)
    after_reachable = _reachable(after)
    assert after_reachable == before_reachable - set(fixes)
    west_path.write_bytes(after.astype("<u2").tobytes())

    report.update({
        "phase": "1.5a.1",
        "changed_visual_cells": 0,
        "changed_xy": [],
        "changed_collision_cells": len(fixes),
        "changed_collision_xy": [list(point) for point in fixes],
        "tree_trunk_conflicts_before": [list(point) for point in tree_conflicts],
        "facade_wall_conflicts_before": [list(point) for point in facade_conflicts],
        "hedge_conflicts_before": [list(point) for point in hedge_conflicts],
        "tree_trunks_walkable": False,
        "tree_collision_note": "Only the two lower trunk cells per 2x2 tree are blocked; canopy cells remain unchanged.",
        "reachability": {
            "spawn_xy": list(SPAWN),
            "reachable_before": len(before_reachable),
            "reachable_after": len(after_reachable),
            "lost_walkable_cells": len(fixes),
            "additional_disconnected_cells": 0,
        },
    })
    (output / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.root, args.output), indent=2))
