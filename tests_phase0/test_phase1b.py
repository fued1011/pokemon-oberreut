"""Phase 1.1b: test desired geometry policy before implementing it."""
import json
import struct
import sys
from pathlib import Path

from PIL import Image
import numpy as np
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/oberreut'))


def test_analytic_policy_minimizes_xor_and_keeps_tiny_footprints():
    from phase1b import choose_buildings
    # One cell is 4 m². A narrow real footprint can miss every cell centre.
    fractions = np.array([[0.1, 3.8], [1.9, 2.1]])
    old = np.ones((2, 2), dtype=bool)
    tiny = [("way/7", box(0, 0, .1, .1), [(0, 0)])]
    result = choose_buildings(fractions, tiny)
    assert result[0, 0]  # preserve the actual tiny footprint, without arbitrary doorway
    assert result[0, 1] and result[1, 1]
    assert not result[1, 0]
    assert np.where(result, 4 - fractions, fractions).sum() < np.where(old, 4 - fractions, fractions).sum()


def test_generated_map_and_reports_preserve_inputs_and_native_contract(tmp_path):
    from phase1b import generate
    output = tmp_path / 'a'
    report = generate(ROOT, output)
    assert report['scope']['crs'] == 'EPSG:25832'
    assert report['scope']['bounds_wsen'] == [453248, 5425984, 453504, 5426112]
    assert report['buildings']['hybrid']['analytic_xor_m2'] <= report['buildings']['centre']['analytic_xor_m2']
    assert report['buildings']['hybrid']['analytic_xor_m2'] < report['buildings']['old']['analytic_xor_m2']
    assert report['buildings']['small_buildings_lost'] == []
    assert report['buildings']['building_ways_lost'] == []
    assert len(report['buildings']['per_way']) == 35
    assert all(row['hybrid_cells'] for row in report['buildings']['per_way'])
    assert report['footways']['old']['blocked_samples'] == 625
    assert sum(r['blocked_samples'] for r in report['footways']['by_way']) == 625
    assert len(report['bottlenecks']['old']) == 34
    assert len(report['bottlenecks']['new']) >= 0
    assert report['footways']['new']['blocked_samples'] == sum(
        row['new_blocked_samples'] for row in report['footways']['by_way'])
    assert report['footways']['new']['blocked_samples'] >= 625
    assert sum(row['causes'].get('outer_perimeter', 0) for row in report['footways']['by_way']) > 0
    for row in report['bottlenecks']['old']:
        assert len(row['blocked_neighbours']) >= 2
        assert all(entry['cause'] in ('building', 'water', 'outer_perimeter', 'other_source_collision')
                   for entry in row['blocked_neighbours'])
    image = np.array(Image.open(output / 'before-after-registered.png'))
    assert image.shape == (310, 1024, 3)
    assert np.any(image[54:310, :512] != image[54:310, 512:])
    for name in ('Oberreut', 'OberreutOst'):
        raw = (output / name / 'map.bin').read_bytes()
        assert len(raw) == 8192
        tiles = struct.unpack('<4096H', raw)
        assert all(v & 0x3000 == 0x3000 for v in tiles)
    second = tmp_path / 'b'
    generate(ROOT, second)
    for rel in ('report.json', 'before-after-registered.png', 'Oberreut/map.bin', 'OberreutOst/map.bin'):
        assert (output / rel).read_bytes() == (second / rel).read_bytes()
    source = json.loads((ROOT / 'data/oberreut/phase1-derived/phase1-manifest.json').read_text())
    assert report['scope']['source_sha256'] == source['source_sha256']


def test_native_layouts_install_phase1b_without_other_metatile_changes():
    for name in ('Oberreut', 'OberreutOst'):
        native = (ROOT / 'data/layouts' / name / 'map.bin').read_bytes()
        refined = (ROOT / 'data/oberreut/phase1b-derived' / name / 'map.bin').read_bytes()
        baseline = (ROOT / 'data/oberreut/phase1-derived' / name / 'map.bin').read_bytes()
        # Phase 1.2 may replace only metatile art in a bounded visual ROI.
        phase12 = ROOT / 'data/oberreut/phase12-derived' / name / 'map.bin'
        assert native == refined or (phase12.exists() and native == phase12.read_bytes())
        after = np.frombuffer(refined, dtype='<u2')
        before = np.frombuffer(baseline, dtype='<u2')
        changed = (after & 1023) != (before & 1023)
        assert np.all(((before[changed] & 1023) == 0x209) | ((after[changed] & 1023) == 0x209))
        assert np.all(((before & 0xc00) != 0) <= ((after & 0xc00) != 0))
