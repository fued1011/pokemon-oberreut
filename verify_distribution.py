#!/usr/bin/env python3
"""Fail closed if a release tree accidentally contains built or upstream art."""
from pathlib import Path
import hashlib
import re
import json

root = Path(__file__).resolve().parent
tracked = [Path(line) for line in __import__('subprocess').check_output(
    ['git', 'ls-files'], cwd=root, text=True).splitlines()]
for rel in tracked:
    if rel.suffix.lower() in {'.gba', '.sav', '.srm', '.elf', '.png', '.jpg', '.jpeg', '.webp', '.bin', '.o', '.zip', '.gz', '.7z', '.so', '.a', '.pal'}:
        raise SystemExit(f'Forbidden tracked asset/build: {rel}')
    if rel.parts[:3] == ('data', 'tilesets', 'secondary'):
        raise SystemExit(f'Tracked tileset asset: {rel}')
    if len(rel.parts) >= 3 and rel.parts[:2] == ('data', 'oberreut') and rel.parts[2].endswith('-derived'):
        raise SystemExit(f'Tracked generated art: {rel}')
patch = (root / 'overlay.patch').read_text()
paths = re.findall(r'^diff --git a/(\S+) b/(\S+)$', patch, re.M)
expected = {
    'data/event_scripts.s', 'data/layouts/layouts.json', 'data/maps/map_groups.json',
    'src/data/region_map/region_map_sections.json', 'src/data/tilesets/graphics.h',
    'src/data/tilesets/headers.h', 'src/data/tilesets/metatiles.h', 'src/new_game.c',
}
assert {a for a, b in paths if a == b} == expected and len(paths) == len(expected)
assert not (root / 'data' / 'oberreut' / 'phase12-derived').exists()
assert hashlib.sha256((root / 'data/oberreut/osm.json').read_bytes()).hexdigest() == 'f5a9fd6e9ec27865b10f73b64d125379f4181cd2112a0d6962d6bc1b1f235150'
assert hashlib.sha256((root / 'data/oberreut/boundary.geojson').read_bytes()).hexdigest() == '2042247c7913d06516c042fd644ec042548227e3a33d2fde3fed4ad00ed49eb2'
print(f'OK: {len(tracked)} tracked paths; no built ROM/tilesets/images; pinned GIS hashes and overlay allowlist')

manifest = json.loads((root / 'distribution.json').read_text())
assert manifest['upstream_commit'] == 'bb1093a7c72d3961d9a37d8e02ad2abc2c866682'
assert set(manifest['patch_files']) == expected
owned = set(manifest['owned_files'])
gis = set(manifest['gis_files'])
assert not owned & gis
assert all((root / p).is_file() for p in owned | gis)
for rel in tracked:
    if rel.parts[0] in ('tools', 'tests_phase0', 'data'):
        assert str(rel) in owned | gis, f'Unregistered distribution file: {rel}'
assert manifest['upstream_commit'] in (root / 'install.sh').read_text()
print('OK: distribution manifest covers all versioned overlay sources')
