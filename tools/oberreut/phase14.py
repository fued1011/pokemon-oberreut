#!/usr/bin/env python3
"""Phase 1.4: tree ring, articulated plaza paving and tram-stop ensemble.

All new pixels come from the reviewed indexed source sheet. This generator
only maps those pixels and the archived GIS geometry onto the Phase 1.3 map;
it never changes collision/elevation bits, GIS masters or building footprints.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import LineString, Point

import phase13 as base

ROI = (16, 10, 58, 45)
ART_SOURCE = Path("graphics/oberreut/julius_leber_phase14.json")
KINDS = (
    "paver_a", "paver_b", "paver_axis", "paver_edge_n",
    "paver_edge_s", "paver_edge_w", "paver_edge_e",
    "tree_nw", "tree_ne", "tree_sw", "tree_se",
    "rail", "ballast", "platform_left", "platform_right",
    "waiting", "stop_sign", "shelter",
)
FIRST_METATILE = max(base.TILE_IDS.values()) + 1
TILE_IDS = {kind: FIRST_METATILE + i for i, kind in enumerate(KINDS)}
TREE_ORIGINS = (
    (20, 19), (28, 19), (36, 19),
    (20, 36), (28, 36), (36, 36),
    (16, 23), (16, 28), (16, 33),
    (42, 23), (42, 28), (42, 33),
)
AXIS_ROWS = (27, 34)


def _pixel_sources(root):
    payload = json.loads((root / ART_SOURCE).read_text())
    assert payload["format"] == "indexed-pixel-source-v1"
    palette = payload["palette_indices"]
    result = {}
    for name, rows in payload["images"].items():
        width = len(rows[0])
        assert rows and all(len(row) == width for row in rows), name
        values = [palette[pixel] for row in rows for pixel in row]
        assert max(values) < 16
        image = Image.new("P", (width, len(rows)))
        image.putpalette([v for rgb in base.base.COLORS for v in rgb] + [0] * (768 - 48))
        image.putdata(values)
        result[name] = image
    assert result["tree"].size == (32, 32)
    for name, image in result.items():
        assert image.size == ((32, 32) if name == "tree" else (16, 16)), (name, image.size)
    return result


def art(root, kind, sources=None):
    sources = sources or _pixel_sources(root)
    if kind.startswith("tree_"):
        x = 0 if kind.endswith(("nw", "sw")) else 16
        y = 0 if kind.endswith(("nw", "ne")) else 16
        return sources["tree"].crop((x, y, x + 16, y + 16))
    if kind == "paver_edge_s":
        return sources["paver_edge_n"].transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if kind == "paver_edge_w":
        return sources["paver_edge_n"].transpose(Image.Transpose.ROTATE_90)
    if kind == "paver_edge_e":
        return sources["paver_edge_n"].transpose(Image.Transpose.ROTATE_270)
    if kind == "platform_left":
        return sources["platform"]
    if kind == "platform_right":
        return sources["platform"].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return sources[kind]


def _track_columns(lines, y, x0, x1):
    scan = LineString([(x0, y + 0.5), (x1, y + 0.5)])
    return {math.floor(point.x) for ident in base.TRACK_WAYS
            for point in [lines[ident].intersection(scan)] if isinstance(point, Point)}


def generate(root, output):
    root = Path(root)
    output = Path(output)
    source = root / "data/oberreut/phase13-derived"
    before = np.frombuffer((source / "Oberreut/map.bin").read_bytes(), dtype="<u2").reshape(64, 64)
    west = before.copy()
    original = np.frombuffer((root / "data/oberreut/phase1b-derived/Oberreut/map.bin").read_bytes(), dtype="<u2").reshape(64, 64)
    terrain = np.array(json.loads((root / "data/oberreut/chunks/0_1.json").read_text())["terrain"]).reshape(128, 128)[32:96, 64:128]
    lines = base.geometry(root)
    x0, y0, x1, y1 = ROI
    platforms = []
    rails = []

    for y in range(y0, y1):
        track_columns = _track_columns(lines, y, x0, x1)
        for x in range(x0, x1):
            kind = int(terrain[y, x])
            symbol = None
            if kind == 6:
                for dx, dy, suffix in ((0, -1, "n"), (0, 1, "s"), (-1, 0, "w"), (1, 0, "e")):
                    if terrain[y + dy, x + dx] != 6:
                        symbol = "paver_edge_" + suffix
                        break
                if symbol is None:
                    symbol = "paver_axis" if y in AXIS_ROWS else ("paver_a" if (x + y) % 2 else "paver_b")
            elif kind == 5:
                symbol = "rail" if x in track_columns else "ballast"
                if symbol == "rail":
                    rails.append([x, y])

            # The OSM features are surveyed as lines; width stays a visual
            # convention, and the pre-existing physics bits remain untouched.
            if kind not in (4, 5) and (original[y, x] & 1023) != 521:
                scan = LineString([(x0, y + 0.5), (x1, y + 0.5)])
                for ident in base.PLATFORM_WAYS:
                    point = lines[ident].intersection(scan)
                    if isinstance(point, Point) and math.floor(point.x) == x:
                        symbol = "platform_right" if ident == 35995212 else "platform_left"
                        platforms.append({"xy": [x, y], "osm_way": ident})

            if symbol:
                west[y, x] = (int(before[y, x]) & 0xFC00) | TILE_IDS[symbol]

    # Waiting strips sit beside, never across, the mapped platform lines.
    waiting_cells = [(44, y) for y in range(12, 22)] + [(50, y) for y in range(23, 45)]
    for x, y in waiting_cells:
        assert terrain[y, x] not in (4, 5)
        west[y, x] = (int(before[y, x]) & 0xFC00) | TILE_IDS["waiting"]
    west[20, 45] = (int(before[20, 45]) & 0xFC00) | TILE_IDS["stop_sign"]
    west[27, 50] = (int(before[27, 50]) & 0xFC00) | TILE_IDS["shelter"]

    tree_symbols = ((0, 0, "tree_nw"), (1, 0, "tree_ne"),
                    (0, 1, "tree_sw"), (1, 1, "tree_se"))
    for x, y in TREE_ORIGINS:
        for dx, dy, symbol in tree_symbols:
            assert terrain[y + dy, x + dx] == 6, (x, y, dx, dy)
            west[y + dy, x + dx] = (int(before[y + dy, x + dx]) & 0xFC00) | TILE_IDS[symbol]

    assert np.array_equal(west & 0xFC00, before & 0xFC00)
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (("Oberreut", west.astype("<u2").tobytes()),
                       ("OberreutOst", (source / "OberreutOst/map.bin").read_bytes())):
        folder = output / name
        folder.mkdir(exist_ok=True)
        (folder / "map.bin").write_bytes(data)

    previous_atlas = Image.open(source / "tiles.png")
    new_rows = math.ceil(len(KINDS) / 8) * 16
    atlas = Image.new("P", (128, previous_atlas.height + new_rows), 0)
    atlas.putpalette(previous_atlas.getpalette())
    atlas.paste(previous_atlas, (0, 0))
    sources = _pixel_sources(root)
    entries = []
    for i, kind in enumerate(KINDS):
        atlas.paste(art(root, kind, sources), ((i % 8) * 16, previous_atlas.height + (i // 8) * 16))
        tx = (i % 8) * 2
        ty = previous_atlas.height // 8 + (i // 8) * 2
        entries.extend([0x6000 + 512 + (ty + dy) * 16 + tx + dx
                        for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))] + [0] * 4)
    assert atlas.width * atlas.height // 64 <= 512 and max(TILE_IDS.values()) < 1024
    atlas.save(output / "tiles.png")
    (output / "metatiles.bin").write_bytes((source / "metatiles.bin").read_bytes() + struct.pack("<" + "H" * len(entries), *entries))
    (output / "metatile_attributes.bin").write_bytes((source / "metatile_attributes.bin").read_bytes() + bytes(2 * len(KINDS)))
    (output / "palettes").mkdir(exist_ok=True)
    for palette in (source / "palettes").glob("*.pal"):
        (output / "palettes" / palette.name).write_bytes(palette.read_bytes())

    report = {
        "phase": "1.4",
        "roi_xyxy": list(ROI),
        "changed_collision_cells": 0,
        "changed_visual_cells": int(np.count_nonzero(west != before)),
        "source_west_sha256": hashlib.sha256(before.tobytes()).hexdigest(),
        "tree_origins": [list(point) for point in TREE_ORIGINS],
        "axis_rows": list(AXIS_ROWS),
        "platform_cells": platforms,
        "waiting_cells": [list(point) for point in waiting_cells],
        "rail_cells": rails,
        "pixel_source": str(ART_SOURCE),
        "metatile_ids": TILE_IDS,
        "secondary_hardware_tiles": atlas.width * atlas.height // 64,
        "secondary_metatiles": max(TILE_IDS.values()) - 511,
        "interpretations": [
            "twelve symbolic 2x2 tree crowns follow the documented ring; exact 2m cell centres are artistic",
            "dark east-west paving bands are visual hierarchy inside the unchanged square polygon",
            "waiting-strip width, shelter cell and stop-sign cell are visual conventions beside mapped platform lines",
        ],
        "references": [
            "docs/JULIUS_LEBER_VISUAL_PLAN.md",
            "OSM archived ways 35995211,35995212,138293860,138293880,4940191",
            "https://stadtlexikon.karlsruhe.de/index.php/De:Lexikon:top-1414",
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
