"""Phase 1.1: GIS geometry, seam consistency, reachability and reproducibility."""
import json
import shutil
import struct
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/oberreut'))


def test_two_connected_native_maps_and_gis_evidence(tmp_path):
    from phase1_map import generate
    generate(ROOT, tmp_path)
    manifest = json.loads((tmp_path / 'phase1-manifest.json').read_text())
    assert manifest['crs'] == 'EPSG:25832'
    assert manifest['metres_per_cell'] == 2 and manifest['pixels_per_cell'] == 16
    assert manifest['origin_easting'] == 453120 and manifest['origin_northing'] == 5426432
    assert manifest['source_sha256']['osm.json'] == 'f5a9fd6e9ec27865b10f73b64d125379f4181cd2112a0d6962d6bc1b1f235150'
    assert manifest['maps']['Oberreut']['crop'] == [64, 160, 64, 64]
    assert manifest['maps']['OberreutOst']['crop'] == [128, 160, 64, 64]
    assert manifest['references']['Julius-Leber-Platz']['map'] == 'Oberreut'
    assert manifest['references']['Oberreut Zentrum']['map'] == 'Oberreut'
    assert manifest['metrics']['buildings']['sampled_symmetric_difference_m2'] >= 0
    assert (tmp_path / 'gis-gba-comparison.png').exists()
    tiles = {}
    for name in ('Oberreut', 'OberreutOst'):
        tiles[name] = struct.unpack('<4096H', (tmp_path / name / 'map.bin').read_bytes())
    # The seam is traversable only where both original source cells permit it.
    chunk = json.loads((ROOT / 'data/oberreut/chunks/0_1.json').read_text())
    east = json.loads((ROOT / 'data/oberreut/chunks/1_1.json').read_text())
    for y in range(64):
        old_pass = not chunk['blocked'][(y + 32) * 128 + 127]
        new_pass = not east['blocked'][(y + 32) * 128]
        assert (not bool(tiles['Oberreut'][y * 64 + 63] & 0xc00)) == (old_pass and y not in (0, 63))
        assert (not bool(tiles['OberreutOst'][y * 64] & 0xc00)) == (new_pass and y not in (0, 63))
    assert all(tiles['OberreutOst'][y * 64 + 63] & 0xc00 for y in range(64))
    assert all(tiles['Oberreut'][x] & 0xc00 and tiles['OberreutOst'][x] & 0xc00 for x in range(64))
    assert any(not (tiles['Oberreut'][y * 64 + 63] & 0xc00) and not (tiles['OberreutOst'][y * 64] & 0xc00) for y in range(64))
    assert manifest['reachability']['reachable_maps'] == ['Oberreut', 'OberreutOst']
    assert manifest['background_classification']['explicit_osm_green_centres'] > 0
    assert manifest['background_classification']['unclassified_default_centres'] > 0
    assert (tmp_path / 'semantic-preview.png').exists()
    from PIL import Image
    semantic_colors = Image.open(tmp_path / 'semantic-preview.png').getcolors(1024 * 512)
    assert semantic_colors is not None
    assert (manifest['background_classification']['explicit_osm_green_centres'] * 64, (82, 139, 92)) in semantic_colors
    assert any((t & 0x3ff) == 0x121 for t in tiles['Oberreut'])


def test_generated_evidence_is_reproducible(tmp_path):
    from phase1_map import generate
    a, b = tmp_path / 'a', tmp_path / 'b'
    generate(ROOT, a)
    generate(ROOT, b)
    for rel in ('phase1-manifest.json', 'gis-gba-comparison.png', 'semantic-preview.png', 'Oberreut/map.bin', 'OberreutOst/map.bin'):
        assert (a / rel).read_bytes() == (b / rel).read_bytes()


def test_rejects_modified_archived_raster_chunk(tmp_path):
    from phase1_map import generate
    source = tmp_path / 'root/data/oberreut'
    shutil.copytree(ROOT / 'data/oberreut', source, ignore=shutil.ignore_patterns('phase1-derived'))
    chunk = source / 'chunks/1_1.json'
    tampered = json.loads(chunk.read_text())
    tampered['terrain'][0] = (tampered['terrain'][0] + 1) % 10
    chunk.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match='Raster snapshot changed'):
        generate(tmp_path / 'root', tmp_path / 'out')


def test_native_registration_and_correct_name():
    maps = json.loads((ROOT / 'data/maps/map_groups.json').read_text())['gMapGroup_TownsAndRoutes']
    sections = json.loads((ROOT / 'src/data/region_map/region_map_sections.json').read_text())['map_sections']
    assert 'OberreutOst' in maps
    assert any(s['id'] == 'MAPSEC_OBERREUT' and s['name'] == 'OBERREUT' for s in sections)
    west = json.loads((ROOT / 'data/maps/Oberreut/map.json').read_text())
    east = json.loads((ROOT / 'data/maps/OberreutOst/map.json').read_text())
    assert west['region_map_section'] == east['region_map_section'] == 'MAPSEC_OBERREUT'
    assert {'map': 'MAP_OBERREUT_OST', 'offset': 0, 'direction': 'right'} in west['connections']
    assert {'map': 'MAP_OBERREUT', 'offset': 0, 'direction': 'left'} in east['connections']
    assert not east['object_events'] and not east['warp_events']
    assert west['show_map_name']
