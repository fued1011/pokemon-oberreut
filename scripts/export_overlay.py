#!/usr/bin/env python3
"""Export allowlisted text sources and a pinned-engine patch into a new directory.

Never copies assets, saves, ROMs or GIS modifications. The candidate is reviewed
and copied into the distribution by the developer; neither input is modified.
"""
import argparse
import difflib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def export(engine, upstream, output):
    manifest = json.loads((ROOT / 'distribution.json').read_text())
    revision = manifest['upstream_commit']
    actual = subprocess.check_output(
        ['git', '-C', str(upstream), 'rev-parse', revision + '^{commit}'], text=True).strip()
    if actual != revision:
        raise ValueError('Pinned upstream commit unavailable')
    if output.exists():
        raise ValueError('Output must not exist; refusing to overwrite a previous export')
    for rel in manifest['gis_files']:
        if (engine / rel).read_bytes() != (ROOT / rel).read_bytes():
            raise ValueError(f'GIS master changed: {rel}')
    sources = {}
    for rel in manifest['owned_files']:
        path = engine / rel
        if path.is_symlink():
            raise ValueError(f'Refusing symlink: {rel}')
        sources[rel] = path.read_text()  # fail before creating output on binary data
    patch = []
    for rel in manifest['patch_files']:
        before = subprocess.check_output(
            ['git', '-C', str(upstream), 'show', f'{revision}:{rel}']).decode()
        after = (engine / rel).read_text()
        if before != after:
            patch.append(f'diff --git a/{rel} b/{rel}\n')
            patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                            fromfile=f'a/{rel}', tofile=f'b/{rel}'))
    sources['overlay.patch'] = ''.join(patch)
    output.mkdir(parents=True)
    for rel, content in sources.items():
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    print(f'Exported {len(sources)} text files to {output}; review before copying/committing.')
    print('Only distribution.json allowlisted files are exported. New files must be registered explicitly.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', type=Path)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.engine.resolve(), args.upstream.resolve(), args.output.resolve())
