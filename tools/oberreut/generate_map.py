#!/usr/bin/env python3
"""Build a native GBA metatile layout from the archived Oberreut GIS raster."""
import argparse
import collections
import hashlib
import json
import struct
from pathlib import Path

CROP = (64, 160, 64, 64)  # x, y, width, height in the V1.2 2 m grid
# Reuse original expansion metatiles; collision is the native 0xC00 map-grid mask.
METATILES = {
    0: 0x001,  # outside: grass, impassable
    1: 0x001,  # grass
    2: 0x121,  # paved: light sand/stone ground from General
    3: 0x121,  # footpath
    4: 0x215,  # road: grey gridded secondary metatile (533)
    5: 0x215,  # tram surface (track geometry is rasterized, not physical rail)
    6: 0x1B3,  # Julius-Leber-Platz: terracotta paving (435)
    7: 0x209,  # building: secondary tiled roof (521)
    8: 0x170,  # water
    9: 0x00D,  # woodland / tall grass (no random encounters here)
}
EXPECTED = {
    "osm.json": "f5a9fd6e9ec27865b10f73b64d125379f4181cd2112a0d6962d6bc1b1f235150",
    "boundary.geojson": "2042247c7913d06516c042fd644ec042548227e3a33d2fde3fed4ad00ed49eb2",
}


def generate(root: Path, output: Path) -> None:
    source = root / "data/oberreut"
    for name, digest in EXPECTED.items():
        actual = hashlib.sha256((source / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"GIS snapshot changed: {name}: {actual}")
    metadata = json.loads((source / "raster-metadata.json").read_text())
    if metadata["source_sha256"] != EXPECTED or metadata["width"] != 256 or metadata["tile_m"] != 2:
        raise ValueError("Unexpected raster metadata")
    chunk = json.loads((source / "chunks/0_1.json").read_text())
    if (chunk["cx"], chunk["cy"]) != (0, 1) or any(len(chunk[k]) != 128 * 128 for k in ("terrain", "blocked")):
        raise ValueError("Unexpected raster chunk shape")
    x0, y0, width, height = CROP
    spawn = (int(metadata["spawn"]["x"]) - x0, int(metadata["spawn"]["y"]) - y0)
    tiles = []
    counts = collections.Counter()
    blocked = 0
    for y in range(y0, y0 + height):
        for x in range(x0, x0 + width):
            i = (y - 128) * 128 + x
            kind = chunk["terrain"][i]
            if kind not in METATILES:
                raise ValueError(f"Unknown terrain code: {kind}")
            counts[metadata["kinds"][kind]] += 1
            solid = bool(chunk["blocked"][i]) or kind in (0, 8) or x in (x0, x0 + width - 1) or y in (y0, y0 + height - 1)
            blocked += solid
            # Elevation 3 makes the player and solid metatiles interact on the same plane.
            tiles.append(0x3000 | (0x0C00 if solid else 0) | METATILES[kind])
    if tiles[spawn[1] * width + spawn[0]] & 0x0C00:
        raise ValueError("GIS spawn is blocked")
    output.mkdir(parents=True, exist_ok=True)
    (output / "map.bin").write_bytes(struct.pack(f"<{len(tiles)}H", *tiles))
    manifest = {
        "source_sha256": EXPECTED,
        "raster_sha256": hashlib.sha256((source / "chunks/0_1.json").read_bytes()).hexdigest(),
        "crop": list(CROP), "spawn": list(spawn),
        "terrain_counts": dict(sorted(counts.items())), "blocked_cells": blocked,
        "encoding": "GBA little-endian u16; bits 0-9 metatile, bits 10-11 collision, bits 12-15 elevation",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "data/layouts/Oberreut")
    args = parser.parse_args()
    generate(args.root, args.output)
