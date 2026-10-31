"""Independent safety/budget checks for the Phase 1.3 refinement."""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/oberreut'))


def test_phase13_preserves_all_physics_footprints_seams_and_east(tmp_path):
    from phase13 import generate, ROI, TILE_IDS
    generate(ROOT,tmp_path)
    before=np.frombuffer((ROOT/'data/oberreut/phase12-derived/Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    after=np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    original=np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    assert np.array_equal(before&0xfc00,after&0xfc00)
    assert np.array_equal(before[(original&1023)==521],after[(original&1023)==521])
    mask=np.ones((64,64),dtype=bool)
    x0,y0,x1,y1=ROI;mask[y0:y1,x0:x1]=False
    assert np.array_equal(before[mask],after[mask])
    assert np.array_equal(before[:,63],after[:,63])
    assert (tmp_path/'OberreutOst/map.bin').read_bytes()==(ROOT/'data/oberreut/phase12-derived/OberreutOst/map.bin').read_bytes()
    assert np.count_nonzero(after!=before)>200
    assert (after[28,30]&0xfc00)==(before[28,30]&0xfc00)


def test_two_tracks_and_mapped_platforms_do_not_invent_crossings(tmp_path):
    from phase13 import generate, TILE_IDS, geometry, PLATFORM_WAYS
    from shapely.geometry import box
    report=generate(ROOT,tmp_path)
    lines=geometry(ROOT)
    after=np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    for y in range(12,40):
        assert (after[y,46]&1023)==TILE_IDS['tram']
        assert (after[y,47]&1023)==TILE_IDS['ballast']
        assert (after[y,48]&1023)==TILE_IDS['tram']
    assert len(report['platform_cells'])>30
    for entry in report['platform_cells']:
        x,y=entry['xy']
        assert entry['osm_way'] in PLATFORM_WAYS
        assert lines[entry['osm_way']].intersects(box(x,y,x+1,y+1))
    assert (after[20,45]&1023)==TILE_IDS['stop_sign']


def test_all_output_bytes_repeat_and_hardware_limits_hold(tmp_path):
    from phase13 import generate, TILE_IDS
    generate(ROOT,tmp_path/'a');generate(ROOT,tmp_path/'b')
    paths=[p.relative_to(tmp_path/'a') for p in (tmp_path/'a').rglob('*') if p.is_file()]
    assert all((tmp_path/'a'/p).read_bytes()==(tmp_path/'b'/p).read_bytes() for p in paths)
    atlas=Image.open(tmp_path/'a/tiles.png')
    assert atlas.mode=='P' and atlas.width*atlas.height//64<=512
    assert np.asarray(atlas).max()<16
    stock=ROOT/'data/tilesets/secondary/petalburg'
    assert np.array_equal(np.asarray(atlas)[:80],np.asarray(Image.open(stock/'tiles.png')))
    for file in ('metatiles.bin','metatile_attributes.bin'):
        assert (tmp_path/'a'/file).read_bytes().startswith((stock/file).read_bytes())
    raw=(tmp_path/'a/metatiles.bin').read_bytes()
    assert len(raw)==(max(TILE_IDS.values())-511)*16
    for ident in TILE_IDS.values():
        values=struct.unpack_from('<8H',raw,(ident-512)*16)
        assert all(v>>12==6 and 512<=(v&1023)<512+atlas.width*atlas.height//64 for v in values[:4])
        assert values[4:]==(0,0,0,0)
    for i in range(16):
        assert (tmp_path/f'a/palettes/{i:02}.pal').read_bytes()==(ROOT/f'data/oberreut/phase12-derived/palettes/{i:02}.pal').read_bytes()


def test_installed_refined_assets_match_latest_generated_output():
    derived = ('phase15a-derived' if (ROOT/'data/oberreut/phase15a-derived').exists()
               else 'phase14-derived' if (ROOT/'data/oberreut/phase14-derived').exists()
               else 'phase13-derived')
    for name in ('Oberreut','OberreutOst'):
        assert (ROOT/f'data/layouts/{name}/map.bin').read_bytes()==(ROOT/f'data/oberreut/{derived}/{name}/map.bin').read_bytes()
    for name in ('tiles.png','metatiles.bin','metatile_attributes.bin'):
        assert (ROOT/f'data/tilesets/secondary/oberreut/{name}').read_bytes()==(ROOT/f'data/oberreut/{derived}/{name}').read_bytes()
