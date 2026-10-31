#!/usr/bin/env bash
# Install this project's overlay onto an independently obtained pinned upstream.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
revision=bb1093a7c72d3961d9a37d8e02ad2abc2c866682
url=https://github.com/rh-hideout/pokeemerald-expansion.git
usage() { echo "Usage: $0 DEST [LOCAL_UPSTREAM_GIT_REPO]" >&2; exit 2; }
[[ $# -ge 1 && $# -le 2 ]] || usage
dest="$1"
[[ ! -e "$dest" ]] || { echo "Destination already exists: $dest" >&2; exit 1; }
mkdir -p "$dest"
dest="$(cd "$dest" && pwd)"
if [[ $# == 2 ]]; then
    [[ "$(git -C "$2" rev-parse "$revision^{commit}")" == "$revision" ]] || { echo 'Upstream revision unavailable' >&2; exit 1; }
    git -C "$2" archive "$revision" | tar -x -C "$dest"
else
    # The tag makes a shallow fetch possible; the full commit is still verified.
    git clone --depth 1 --branch expansion/1.17.1 "$url" "$dest/upstream-fetch"
    [[ "$(git -C "$dest/upstream-fetch" rev-parse HEAD)" == "$revision" ]] || { echo 'Upstream tag no longer points to pinned commit' >&2; exit 1; }
    (cd "$dest/upstream-fetch" && git archive HEAD) | tar -x -C "$dest"
    rm -rf "$dest/upstream-fetch"
fi
# git apply checks complete context; it does not silently overwrite unrelated files.
git -C "$dest" apply --check "$here/overlay.patch"
git -C "$dest" apply "$here/overlay.patch"
# Upstream's history make target rejects exported source archives without this flag.
touch "$dest/.histignore"
# Explicit allowlist: do not copy the public repo's .git, upstream assets, or builds.
files=(
 data/layouts/Oberreut/manifest.json
 data/maps/Oberreut/map.json data/maps/Oberreut/scripts.inc
 data/maps/OberreutOst/map.json data/maps/OberreutOst/scripts.inc
 tools/oberreut/generate_map.py tools/oberreut/phase1_map.py
 tools/oberreut/phase1b.py tools/oberreut/phase12.py
 tools/oberreut/requirements-phase1.txt
 data/oberreut/osm.json data/oberreut/boundary.geojson
 data/oberreut/overpass-query.ql data/oberreut/overpass-endpoint.txt
 data/oberreut/raster-metadata.json data/oberreut/metadata.json
 data/oberreut/stadtteile-metadata.json data/oberreut/sources-ledger.json
)
for file in "${files[@]}" "$here"/data/oberreut/chunks/*.json "$here"/tests_phase0/*.py; do
    if [[ "$file" == "$here"/* ]]; then rel="${file#"$here"/}"; else rel="$file"; file="$here/$file"; fi
    mkdir -p "$dest/$(dirname "$rel")"
    cp "$file" "$dest/$rel"
done
# The border is identical to stock Route101; never distribute the byte copy.
mkdir -p "$dest/data/layouts/OberreutOst" "$dest/data/tilesets/secondary/oberreut"
cp "$dest/data/layouts/Route101/border.bin" "$dest/data/layouts/Oberreut/border.bin"
cp "$dest/data/layouts/Route101/border.bin" "$dest/data/layouts/OberreutOst/border.bin"
python_bin="${PHASE1_PYTHON:-python3}"
"$python_bin" -c 'import numpy, shapely, pyproj, PIL, pytest'
"$python_bin" "$dest/tools/oberreut/generate_map.py" --root "$dest" --output "$dest/data/layouts/Oberreut"
"$python_bin" "$dest/tools/oberreut/phase1_map.py" --root "$dest" --output "$dest/data/oberreut/phase1-derived"
"$python_bin" "$dest/tools/oberreut/phase1b.py" --root "$dest" --output "$dest/data/oberreut/phase1b-derived" >/dev/null
"$python_bin" "$dest/tools/oberreut/phase12.py" --root "$dest" --output "$dest/data/oberreut/phase12-derived" >/dev/null
for name in Oberreut OberreutOst; do
    cp "$dest/data/oberreut/phase12-derived/$name/map.bin" "$dest/data/layouts/$name/map.bin"
done
for name in tiles.png metatiles.bin metatile_attributes.bin; do
    cp "$dest/data/oberreut/phase12-derived/$name" "$dest/data/tilesets/secondary/oberreut/$name"
done
mkdir -p "$dest/data/tilesets/secondary/oberreut/palettes"
cp "$dest"/data/oberreut/phase12-derived/palettes/*.pal "$dest/data/tilesets/secondary/oberreut/palettes/"
echo "Installed at $dest; generated assets remain in this separate upstream tree."
