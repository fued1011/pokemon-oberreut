#!/usr/bin/env bash
# Rebuild only generated Oberreut files in an already installed private engine.
set -euo pipefail
[[ $# == 1 ]] || { echo "Usage: $0 PRIVATE_ENGINE" >&2; exit 2; }
root="$(cd "$1" && pwd)"
[[ -f "$root/src/new_game.c" && -f "$root/data/tilesets/secondary/petalburg/tiles.png" ]] || exit 1
python_bin="${PHASE1_PYTHON:-python3}"
for phase in phase1_map phase1b phase12 phase13 phase14; do
    output="$phase"
    [[ "$phase" != phase1_map ]] || output=phase1
    "$python_bin" "$root/tools/oberreut/$phase.py" --root "$root" --output "$root/data/oberreut/$output-derived"
done
for name in Oberreut OberreutOst; do
    cp "$root/data/oberreut/phase14-derived/$name/map.bin" "$root/data/layouts/$name/map.bin"
done
for name in tiles.png metatiles.bin metatile_attributes.bin; do
    cp "$root/data/oberreut/phase14-derived/$name" "$root/data/tilesets/secondary/oberreut/$name"
done
cp "$root"/data/oberreut/phase14-derived/palettes/*.pal "$root/data/tilesets/secondary/oberreut/palettes/"
