#!/usr/bin/env python3
"""Record hashes of private results without copying any protected asset."""
import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('engine', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
root = args.engine.resolve()
paths = [root / 'pokeemerald.gba', root / 'pokeemerald.map']
for rel in ('data/oberreut/phase12-derived', 'data/oberreut/phase13-derived', 'data/oberreut/phase14-derived', 'data/oberreut/phase15a-derived', 'data/oberreut/phase15a1-derived', 'logs'):
    paths.extend(p for p in (root / rel).rglob('*') if p.is_file())
result = {
    'upstream_commit': json.loads((Path(__file__).resolve().parents[1] / 'distribution.json').read_text())['upstream_commit'],
    'python': platform.python_version(),
    'compiler': subprocess.check_output(['arm-none-eabi-gcc', '--version'], text=True).splitlines()[0],
    'files': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
}
with args.output.open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(f'Recorded {len(paths)} file hashes in {args.output}')
