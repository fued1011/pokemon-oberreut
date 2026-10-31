#!/usr/bin/env python3
"""Phase 1.5a: northern Julius-Leber-Platz residential block.

The phase replaces hardware pixels belonging to unused Phase 1.4 metatiles,
then uses those metatiles only inside the existing northern building footprint.
Map physics, GIS sources, the atlas size and every other scene stay unchanged.
"""
import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

import phase14

ART_SOURCE = Path("graphics/oberreut/north_residential_phase15a.json")
SLOT_IDS = {
    "roof_ridge": 656,
    "roof_slope": 658,
    "roof_gable_l": 662,
    "roof_gable_r": 674,
    "facade_window": 679,
    "facade_balcony": 685,
    "facade_stair": 686,
    "facade_plain": 687,
    "entrance": 696,
    "base_window": 692,
    "base_plain": 693,
    "hedge": 694,
    "wall_edge": 695,
}
ROOF_GABLES = ((29, 30), (36, 37))
STAIRWELLS = {29, 30, 36, 37}
BALCONIES = {24, 33}
WINDOWS = {23, 27, 32, 35}
ENTRANCES = {25, 34}
HEDGES = {20, 39}


def _map(path):
    return np.frombuffer(path.read_bytes(), dtype="<u2").reshape(64, 64)


def _art(root):
    payload = json.loads((root / ART_SOURCE).read_text())
    assert payload["format"] == "indexed-pixel-source-v1"
    palette = payload["palette_indices"]
    images = {}
    for name in SLOT_IDS:
        rows = payload["images"][name]
        assert len(rows) == 16 and all(len(row) == 16 for row in rows), name
        values = [palette[pixel] for row in rows for pixel in row]
        assert max(values) < 16
        image = Image.new("P", (16, 16))
        image.putdata(values)
        images[name] = image
    return images


def _place(west, before, x, y, kind):
    west[y, x] = (int(before[y, x]) & 0xFC00) | SLOT_IDS[kind]


def generate(root, output):
    root = Path(root)
    output = Path(output)
    source = root / "data/oberreut/phase14-derived"
    before = _map(source / "Oberreut/map.bin")
    east = (source / "OberreutOst/map.bin").read_bytes()
    west = before.copy()

    used = set(int(value) for value in before.ravel() & 1023)
    used.update(int(value) for value in np.frombuffer(east, dtype="<u2") & 1023)
    assert not used.intersection(SLOT_IDS.values())

    # Roof stays within the surveyed x22..38 footprint. Two shallow gables
    # align with the stairwell bays and break up the long dark roofline.
    for y, default in ((10, "roof_ridge"), (11, "roof_slope"), (12, "roof_slope")):
        for x in range(22, 39):
            kind = default
            for left, right in ROOF_GABLES:
                if x == left:
                    kind = "roof_gable_l"
                elif x == right:
                    kind = "roof_gable_r"
            _place(west, before, x, y, kind)

    # Four visible residential storeys, including a grounded entrance level.
    # The staggered footprint in rows 13..15 is inherited unchanged.
    for y in range(13, 17):
        left = 21
        for x in range(left, 39):
            if x in STAIRWELLS:
                kind = "facade_stair"
            elif y == 16 and x in ENTRANCES:
                kind = "entrance"
            elif y == 16 and x in WINDOWS:
                kind = "base_window"
            elif y == 16:
                kind = "base_plain"
            elif x in BALCONIES:
                kind = "facade_balcony"
            elif x in WINDOWS:
                kind = "facade_window"
            else:
                kind = "facade_plain"
            if x in (left, 38):
                kind = "wall_edge"
            _place(west, before, x, y, kind)

    for x in HEDGES:
        _place(west, before, x, 16, "hedge")

    assert np.array_equal(west & 0xFC00, before & 0xFC00)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (("Oberreut", west.astype("<u2").tobytes()), ("OberreutOst", east)):
        folder = output / name
        folder.mkdir(exist_ok=True)
        (folder / "map.bin").write_bytes(data)

    raw_metatiles = (source / "metatiles.bin").read_bytes()
    users = defaultdict(list)
    count = len(raw_metatiles) // 16
    for ident in range(512, 512 + count):
        values = struct.unpack_from("<8H", raw_metatiles, (ident - 512) * 16)
        for value in values[:4]:
            users[value & 1023].append(ident)

    atlas = Image.open(source / "tiles.png").copy()
    images = _art(root)
    replaced_hardware_tiles = {}
    for kind, ident in SLOT_IDS.items():
        values = struct.unpack_from("<8H", raw_metatiles, (ident - 512) * 16)
        hardware = [value & 1023 for value in values[:4]]
        assert values[4:] == (0, 0, 0, 0)
        assert all(value >> 12 == 6 for value in values[:4])
        assert all(users[tile] == [ident] for tile in hardware), (kind, hardware)
        source_image = images[kind]
        for index, tile in enumerate(hardware):
            relative = tile - 512
            box = ((relative % 16) * 8, (relative // 16) * 8)
            crop = source_image.crop(((index % 2) * 8, (index // 2) * 8,
                                      (index % 2 + 1) * 8, (index // 2 + 1) * 8))
            atlas.paste(crop, box)
        replaced_hardware_tiles[kind] = hardware

    previous_atlas = Image.open(source / "tiles.png")
    assert atlas.size == previous_atlas.size
    assert atlas.width * atlas.height // 64 == 480
    atlas.save(output / "tiles.png")
    for name in ("metatiles.bin", "metatile_attributes.bin"):
        (output / name).write_bytes((source / name).read_bytes())
    (output / "palettes").mkdir(exist_ok=True)
    for palette in (source / "palettes").glob("*.pal"):
        (output / "palettes" / palette.name).write_bytes(palette.read_bytes())

    tree_trunks = [(x, y + 1) for x, y in phase14.TREE_ORIGINS]
    tree_trunks_walkable = all((west[y, x] & 0x0C00) == 0 for x, y in tree_trunks)
    changed = np.argwhere(west != before)
    report = {
        "phase": "1.5a",
        "changed_collision_cells": 0,
        "changed_visual_cells": int(len(changed)),
        "changed_xy": [[int(x), int(y)] for y, x in changed],
        "source_west_sha256": hashlib.sha256(before.tobytes()).hexdigest(),
        "pixel_source": str(ART_SOURCE),
        "reused_metatile_ids": SLOT_IDS,
        "replaced_hardware_tiles": replaced_hardware_tiles,
        "secondary_hardware_tiles_before": 480,
        "secondary_hardware_tiles_after": 480,
        "visible_storey_rows": [13, 14, 15, 16],
        "stairwell_columns": sorted(STAIRWELLS),
        "entrance_columns": sorted(ENTRANCES),
        "hedge_cells": [[x, 16] for x in sorted(HEDGES)],
        "tree_trunks_walkable": tree_trunks_walkable,
        "tree_collision_note": (
            "Phase 1.4 tree lower cells retain walkable collision bits; documented only, "
            "because Phase 1.5a is forbidden from changing collision."
        ),
        "references": [
            "docs/JULIUS_LEBER_VISUAL_PLAN.md",
            "docs/julius-leber-reference.svg",
            "existing GIS-derived building footprint",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.root, args.output), indent=2))
