"""Phase 1.2 local visual slice, without opening any paths."""
import json
import struct
import sys
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/oberreut'))


def test_local_graphics_preserve_collision_and_geographic_cells(tmp_path):
    from phase12 import generate, ROI, TILE_IDS
    generate(ROOT, tmp_path)
    before = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64)
    after = np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64)
    east = (tmp_path/'OberreutOst/map.bin').read_bytes()
    assert east == (ROOT/'data/oberreut/phase1b-derived/OberreutOst/map.bin').read_bytes()
    assert np.array_equal(before & 0xfc00, after & 0xfc00)
    x0,y0,x1,y1 = ROI
    changed = (before & 1023) != (after & 1023)
    assert changed.sum() > 200
    assert not changed[:y0].any() and not changed[y1:].any()
    assert not changed[:, :x0].any() and not changed[:, x1:].any()
    assert set((after[changed] & 1023).tolist()) <= set(TILE_IDS.values())
    assert after[28,30] & 0xc00 == 0
    assert before[28,30] & 0xc00 == 0
    assert np.array_equal(before[:,63] & 0xc00, after[:,63] & 0xc00)
    # Finite roofs/elevation within the existing mask; no continuous facade band.
    assert (after[12,22] & 1023) == TILE_IDS['roof_end_l']
    assert (after[12,38] & 1023) == TILE_IDS['roof_end_r']
    assert (after[14,23] & 1023) == TILE_IDS['wall_window']
    assert (after[14,29] & 1023) == TILE_IDS['wall_shadow']
    assert (after[18,30] & 1023) == TILE_IDS['tree_bed_l']
    assert (before[18,30] & 1023) == 289
    assert (after[16,30] & 1023) == TILE_IDS['unknown']
    assert (tmp_path/'Oberreut/map.bin').stat().st_size == 8192


def test_tileset_hardware_budget_and_reproducibility(tmp_path):
    from phase12 import generate, TILE_IDS, ROI
    generate(ROOT, tmp_path/'first')
    generate(ROOT, tmp_path/'second')
    rels = ['Oberreut/map.bin','OberreutOst/map.bin','tiles.png','metatiles.bin','metatile_attributes.bin','palettes/00.pal','manifest.json']
    assert all((tmp_path/'first'/p).read_bytes() == (tmp_path/'second'/p).read_bytes() for p in rels)
    im = Image.open(tmp_path/'first/tiles.png')
    assert im.mode == 'P' and im.width % 8 == 0 and im.height % 8 == 0
    assert len(im.getcolors()) <= 16
    hardware = im.width * im.height // 64
    assert hardware <= 512
    raw = (tmp_path/'first/metatiles.bin').read_bytes()
    assert (tmp_path/'first/metatiles.bin').read_bytes().startswith((ROOT/'data/tilesets/secondary/petalburg/metatiles.bin').read_bytes())
    assert (tmp_path/'first/metatile_attributes.bin').read_bytes().startswith((ROOT/'data/tilesets/secondary/petalburg/metatile_attributes.bin').read_bytes())
    assert (tmp_path/'first/palettes/07.pal').read_bytes() == (ROOT/'data/tilesets/secondary/petalburg/palettes/07.pal').read_bytes()
    old = (ROOT/'data/tilesets/secondary/petalburg/metatiles.bin').read_bytes()
    west = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64).copy()
    x0,y0,x1,y1 = ROI
    west[y0:y1,x0:x1] = 0
    east = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/OberreutOst/map.bin').read_bytes(),dtype='<u2')
    stock_ids = set((west & 1023).flatten().tolist()) | set((east & 1023).tolist())
    for stock_id in stock_ids:
        if stock_id < 512:
            continue  # palette of the independent primary tileset
        entries = struct.unpack_from('<8H',old,(stock_id-512)*16)
        assert all((v >> 12) != 6 for v in entries)
    assert len(raw) == (max(TILE_IDS.values()) - 511)*16
    for index in TILE_IDS.values():
        entries = struct.unpack_from('<8H',raw,(index-512)*16)
        assert all(512 <= (v&1023) < 512+hardware and v>>12 == 6 for v in entries[:4])
        assert entries[4:] == (0,0,0,0)  # upstream transparent top BG tile
    assert len((tmp_path/'first/metatile_attributes.bin').read_bytes()) == len(raw)//8
    assert json.loads((tmp_path/'first/manifest.json').read_text())['cell_m'] == 2


def test_native_porymap_tileset_wiring_and_installed_layouts():
    layouts = json.loads((ROOT/'data/layouts/layouts.json').read_text())['layouts']
    selected = [x for x in layouts if x['id'] in ('LAYOUT_OBERREUT','LAYOUT_OBERREUT_OST')]
    assert len(selected) == 2
    assert all(x['secondary_tileset'] == 'gTileset_Oberreut' for x in selected)
    for name in ('Oberreut','OberreutOst'):
        assert (ROOT/f'data/layouts/{name}/map.bin').read_bytes() == (ROOT/f'data/oberreut/phase12-derived/{name}/map.bin').read_bytes()
    for name in ('tiles.png','metatiles.bin','metatile_attributes.bin'):
        assert (ROOT/f'data/tilesets/secondary/oberreut/{name}').read_bytes() == (ROOT/f'data/oberreut/phase12-derived/{name}').read_bytes()
    assert 'gTileset_Oberreut' in (ROOT/'src/data/tilesets/headers.h').read_text()
    assert 'gMetatiles_Oberreut' in (ROOT/'src/data/tilesets/metatiles.h').read_text()
    assert 'gTilesetTiles_Oberreut' in (ROOT/'src/data/tilesets/graphics.h').read_text()


def test_phase12b_facade_has_distinct_balconies_doors_and_a_bounded_roof(tmp_path):
    from phase12 import generate, TILE_IDS
    generate(ROOT, tmp_path)
    after = np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64) & 1023
    before = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64) & 1023
    assert after[13,24] == TILE_IDS['balcony_upper']
    assert after[14,24] == TILE_IDS['balcony_rail']
    assert after[14,33] == TILE_IDS['balcony_rail']
    assert after[15,25] == TILE_IDS['wall_entrance']
    assert after[15,34] == TILE_IDS['wall_entrance']
    assert after[13,22] == TILE_IDS['wall_corner_l']
    assert after[15,38] == TILE_IDS['wall_corner_r']
    assert after[12,23] == TILE_IDS['roof_eave']
    assert before[16,25] != 521  # doors never invent an opening outside the footprint
    for x,y in ((24,13),(24,14),(25,15),(33,14),(34,15)):
        assert before[y,x] == 521
    assert (after[13,39] != TILE_IDS['wall_plain'])


def test_phase12b_original_tiles_encode_distinct_architectural_details():
    from phase12 import _art
    import numpy as np
    balcony = np.asarray(_art('balcony_rail'))
    window = np.asarray(_art('wall_window'))
    entrance = np.asarray(_art('wall_entrance'))
    assert not np.array_equal(balcony, window)
    assert not np.array_equal(entrance, window)
    assert len(np.unique(balcony)) >= 4
    assert len(np.unique(entrance)) >= 4


def test_phase12b_plaza_has_local_paving_variation_without_rewriting_terrain(tmp_path):
    from phase12 import generate, TILE_IDS
    generate(ROOT, tmp_path)
    after = np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64)
    before = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64)
    paving = after[22:35,23:44] & 1023
    assert TILE_IDS['square'] in paving
    assert TILE_IDS['square_warm'] in paving
    assert TILE_IDS['square_cool'] in paving
    assert np.array_equal(before & 0xfc00, after & 0xfc00)
    assert np.array_equal(before[:,63], after[:,63])


def test_phase12b_planters_stay_inside_mapped_green_and_have_two_halves(tmp_path):
    from phase12 import generate, TILE_IDS
    generate(ROOT, tmp_path)
    after = np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64) & 1023
    before = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(), dtype='<u2').reshape(64,64) & 1023
    for x in (23,30,38):
        for y in (18,38):
            assert (after[y,x],after[y,x+1]) == (TILE_IDS['tree_bed_l'],TILE_IDS['tree_bed_r'])
            assert (before[y,x],before[y,x+1]) == (289,289)


def test_northern_roof_ridge_and_plane_use_only_existing_building_cells(tmp_path):
    from phase12 import generate, TILE_IDS
    generate(ROOT, tmp_path)
    before = np.frombuffer((ROOT/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(),
                           dtype='<u2').reshape(64,64)
    after = np.frombuffer((tmp_path/'Oberreut/map.bin').read_bytes(),
                          dtype='<u2').reshape(64,64)
    # This part of the source mask is the roof over the facade on rows 13-15.
    assert (after[10,23] & 1023) == TILE_IDS['roof_ridge']
    assert (after[11,23] & 1023) == TILE_IDS['roof_plane']
    for y in (10,11):
        for x in range(64):
            if (before[y,x] & 1023) != 521 or not 22 <= x <= 38:
                assert after[y,x] == before[y,x], (x,y)
    assert np.array_equal(after & 0xfc00, before & 0xfc00)
    assert (after[10,23] & 0xfc00) == (before[10,23] & 0xfc00)
