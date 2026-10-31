#!/usr/bin/env python3
"""Original, bounded 4bpp art; the pinned GIS masks and collision are immutable.

A visual interpretation of the 2014 Julius-Leber-Platz photograph, not a survey
of individual buildings or a license to reproduce that photograph.
"""
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROI = (20, 10, 58, 45)  # west map, half-open; rows 10-11: existing facade roof only
KINDS = ('square', 'path', 'tram', 'green', 'unknown', 'road',
         'tree_bed', 'roof_ridge', 'roof_plane', 'roof_eave',
         'roof_gable_l', 'roof_gable_r', 'roof_end_l', 'roof_end_r',
         'wall_plain', 'wall_window', 'wall_pier', 'wall_end_l',
         'wall_end_r', 'wall_base', 'wall_base_window', 'wall_shadow',
         'roof_compact', 'roof_compact_edge', 'balcony_upper',
         'balcony_rail', 'wall_entrance', 'wall_corner_l', 'wall_corner_r',
         'square_warm', 'square_cool', 'tree_bed_l', 'tree_bed_r')
TILE_IDS = {name: 656 + i for i, name in enumerate(KINDS)}
# RGB555-exact; index 0 reserved for transparent BG overlays.
COLORS = [(248,248,248),(40,48,56),(72,88,88),(128,144,144),
          (176,184,176),(224,224,208),(248,248,232),(184,152,120),
          (136,96,80),(96,64,64),(72,112,88),(96,152,104),
          (144,184,128),(176,104,80),(216,152,104),(224,192,144)]


def _art(kind):
    if kind in ('tree_bed_l','tree_bed_r'):
        # A paired, round shrub-and-tree island, entirely inside two mapped
        # green cells. Both halves derive from one drawing so edges align.
        pair = Image.new('P',(32,16),11)
        pen = ImageDraw.Draw(pair)
        pen.ellipse((1,6,30,15),fill=3)
        pen.ellipse((3,7,28,14),fill=10)
        pen.rectangle((14,7,17,13),fill=8)
        pen.ellipse((7,0,25,11),fill=10)
        pen.ellipse((9,0,21,6),fill=12)
        pen.ellipse((18,3,24,8),fill=11)
        for px,py in ((10,6),(14,2),(21,5),(24,9)):
            pen.point((px,py),fill=12)
        return pair.crop((0 if kind.endswith('_l') else 16,0,
                          16 if kind.endswith('_l') else 32,16))
    base = {'square':5, 'square_warm':5, 'square_cool':5,
            'path':4, 'tram':2, 'green':11,
            'tree_bed':5, 'unknown':4, 'road':2}.get(kind)
    if base is None:
        base = 3 if kind.startswith('roof') else 6
    im = Image.new('P', (16, 16), base)
    d = ImageDraw.Draw(im)
    if kind.startswith('roof'):
        if kind == 'roof_ridge':
            d.polygon([(0,0),(15,0),(15,4),(0,7)],fill=5)
            d.line((0,7,15,4), fill=2)
            d.polygon([(0,9),(15,6),(15,15),(0,15)],fill=4)
        elif kind == 'roof_plane':
            d.polygon([(0,0),(15,0),(15,15),(0,15)],fill=4)
            d.polygon([(0,0),(15,0),(15,6),(0,12)],fill=5)
            d.line((0,12,15,6),fill=3)
        elif kind == 'roof_eave':
            d.polygon([(0,0),(15,0),(15,10),(0,14)],fill=4)
            d.line((0,14,15,10),fill=2, width=2)
            d.rectangle((0,14,15,15),fill=1)
        elif kind in ('roof_gable_l','roof_gable_r'):
            d.polygon([(0,0),(15,0),(15,15),(0,15)],fill=4)
            if kind == 'roof_gable_l':
                d.polygon([(0,15),(15,1),(15,15)],fill=6)
                d.line((0,15,15,1),fill=2,width=2)
                d.rectangle((11,10,13,13),fill=2)
            else:
                d.polygon([(0,1),(15,15),(0,15)],fill=6)
                d.line((0,1,15,15),fill=2,width=2)
                d.rectangle((3,10,5,13),fill=2)
        elif kind in ('roof_end_l','roof_end_r'):
            d.rectangle((0,0,15,15),fill=4)
            d.polygon([(0,0),(15,0),(15,8),(0,14)],fill=5)
            d.line((0,14,15,8),fill=2,width=2)
            edge=0 if kind=='roof_end_l' else 14
            d.rectangle((edge,0,edge+1,15),fill=2)
        else:
            d.polygon([(0,0),(15,0),(15,13),(0,13)],fill=4)
            d.line((0,3,15,3),fill=5)
            if kind == 'roof_compact_edge':
                d.rectangle((0,13,15,15),fill=2)
    elif kind.startswith('wall') or kind.startswith('balcony'):
        d.rectangle((0,0,15,15),fill=6)
        d.rectangle((0,0,15,1),fill=5)  # fine cornice, not a window strip
        if kind in ('wall_window','wall_base_window'):
            d.rectangle((3,3,12,13),fill=5)
            d.rectangle((4,4,11,11),fill=2)
            d.rectangle((5,5,10,10),fill=3)
            d.line((8,5,8,11),fill=5)
            d.line((3,13,12,13),fill=4)
        elif kind in ('balcony_upper','balcony_rail'):
            # A recessed glazed bay continues across two storeys. The lower
            # tile gains a shallow slab and open iron rail; no passable cell.
            d.rectangle((2,2,13,13),fill=5)
            d.rectangle((3,3,12,12),fill=2)
            d.rectangle((4,4,11,11),fill=3)
            d.rectangle((7,3,8,12),fill=5)
            d.line((3,13,12,13),fill=4)
            if kind == 'balcony_rail':
                d.rectangle((0,10,15,11),fill=3)
                for x in (1,5,10,14):
                    d.line((x,11,x,14),fill=2)
                d.rectangle((0,14,15,15),fill=4)
        elif kind == 'wall_entrance':
            d.rectangle((2,2,13,15),fill=5)
            d.rectangle((3,4,12,15),fill=2)
            d.rectangle((4,5,11,8),fill=3)  # transom glazing
            d.rectangle((4,9,11,15),fill=8)
            d.line((8,9,8,15),fill=1)
            d.point((6,12),fill=5)
            d.rectangle((1,0,14,2),fill=4)  # short entrance canopy
        elif kind in ('wall_corner_l','wall_corner_r'):
            edge = 0 if kind == 'wall_corner_l' else 12
            d.rectangle((edge,0,edge+3,15),fill=5)
            d.line((edge+3,1,edge+3,15),fill=3)
            d.rectangle((edge+5 if edge==0 else 2,4,
                         edge+9 if edge==0 else 6,10),fill=4)
        elif kind == 'wall_pier':
            d.rectangle((6,2,9,15),fill=5)
            d.line((6,3,6,15),fill=4)
        elif kind in ('wall_end_l','wall_end_r'):
            edge = 0 if kind=='wall_end_l' else 13
            d.rectangle((edge,0,edge+2,15),fill=3)
            d.rectangle((edge+3 if edge==0 else 3,4,edge+8 if edge==0 else 8,11),fill=4)
        elif kind == 'wall_shadow':
            d.rectangle((0,0,4,15),fill=3)
            d.line((5,2,5,15),fill=4)
        if kind.startswith('wall_base') or kind == 'wall_entrance':
            d.rectangle((0,15,15,15),fill=3)
    elif kind == 'tram':
        d.rectangle((3,0,4,15), fill=1)
        d.rectangle((11,0,12,15), fill=1)
        for y in (2,10):
            d.line((2,y,13,y),fill=7)
            d.line((2,y+1,13,y+1),fill=8)
    elif kind == 'road':
        d.line((0,0,15,0),fill=3)
        d.line((0,15,15,15),fill=1)
    elif kind in ('square','square_warm','square_cool'):
        # Separate handmade stone tones; identical staggered joints in all
        # variants, so the mosaic doesn't read as a road or striped walkway.
        if kind == 'square_warm':
            d.rectangle((1,1,7,6),fill=6)
            d.rectangle((5,9,14,14),fill=6)
        elif kind == 'square_cool':
            d.rectangle((9,1,14,6),fill=4)
            d.rectangle((1,9,3,14),fill=4)
        d.line((0,7,15,7),fill=4)
        d.line((0,15,15,15),fill=4)
        d.line((8,0,8,6),fill=4)
        d.line((4,8,4,14),fill=4)
    elif kind == 'path':
        d.line((0,8,15,8),fill=5)
        d.line((8,0,8,15),fill=5)
    elif kind == 'tree_bed':
        # Planter in an already-green source cell; never opens a crossing.
        d.ellipse((0,5,15,15),fill=3)
        d.ellipse((2,6,13,14),fill=10)
        d.rectangle((7,6,8,11),fill=8)
        d.ellipse((2,0,13,10),fill=10)
        d.ellipse((4,0,11,7),fill=12)
    elif kind == 'green':
        for x,y in ((3,3),(11,2),(7,11),(14,13)):
            d.ellipse((x-2,y-2,x+2,y+2),fill=10)
            d.point((x-1,y-1),fill=12)
    elif kind == 'unknown':
        d.line((0,15,15,15),fill=5)
    return im


def _building_symbol(x,y,old):
    # Two finite, readable elevations inside the existing northern footprint.
    # The split/gables are illustrative modules, not measured separate houses.
    if 21 <= x <= 38 and 10 <= y <= 15:
        if y <= 12:
            if x in (21,22): return 'roof_end_l'
            if x == 38: return 'roof_end_r'
            if x in (29,36): return 'roof_gable_l'
            if x in (30,37): return 'roof_gable_r'
            return ('roof_ridge','roof_plane','roof_eave')[y-10]
        if x in (21,22): return 'wall_corner_l' if x == 22 else 'wall_end_l'
        if x == 38: return 'wall_corner_r'
        if x in (29,30,36,37): return 'wall_shadow'
        if y == 15 and x in (25,34): return 'wall_entrance'
        if x in (24,33) and y in (13,14):
            return 'balcony_upper' if y == 13 else 'balcony_rail'
        if y == 15:
            return 'wall_base_window' if x in (23,27,32,35) else 'wall_base'
        if x in (23,27,32,35): return 'wall_window'
        return 'wall_pier' if x in (22,28,31) else 'wall_plain'
    # Remaining GIS building masks: bounded generic roof/eave, not endless facade.
    south = y+1 < 64 and (old[y+1,x] & 1023) == 521
    return 'roof_compact' if south else 'roof_compact_edge'


def _tileset(root, output):
    stock = root/'data/tilesets/secondary/petalburg'
    count = max(TILE_IDS.values()) - 511
    atlas = Image.new('P',(128,80+((len(KINDS)+7)//8)*16),0)
    atlas.putpalette([v for rgb in COLORS for v in rgb]+[0]*(768-48))
    original = Image.open(stock/'tiles.png')
    assert original.mode == 'P' and original.size == (128,80)
    atlas.paste(original,(0,0))
    blocks=[]
    for i,kind in enumerate(KINDS):
        atlas.paste(_art(kind),((i%8)*16,80+(i//8)*16))
        x=(i%8)*2; y=10+(i//8)*2
        blocks.extend([0x6000+512+(y+dy)*16+x+dx for dy,dx in ((0,0),(0,1),(1,0),(1,1))])
        blocks.extend([0,0,0,0])  # transparent upper BG, original primary tile 0
    output.mkdir(parents=True,exist_ok=True)
    atlas.save(output/'tiles.png')
    (output/'metatiles.bin').write_bytes((stock/'metatiles.bin').read_bytes()+struct.pack('<'+'H'*len(blocks),*blocks))
    (output/'metatile_attributes.bin').write_bytes((stock/'metatile_attributes.bin').read_bytes()+bytes(2*len(KINDS)))
    pals=output/'palettes'; pals.mkdir(exist_ok=True)
    text='JASC-PAL\n0100\n16\n'+''.join(f'{r} {g} {b}\n' for r,g,b in COLORS)
    for i in range(16):
        dest=pals/f'{i:02}.pal'
        if i==6: dest.write_text(text)
        else: dest.write_bytes((stock/'palettes'/dest.name).read_bytes())
    return count,atlas.width*atlas.height//64


def generate(root,output):
    root=Path(root); output=Path(output)
    source=root/'data/oberreut/phase1b-derived'
    west=np.frombuffer((source/'Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64).copy()
    original=west.copy()
    east=(source/'OberreutOst/map.bin').read_bytes()
    chunk=json.loads((root/'data/oberreut/chunks/0_1.json').read_text())
    x0,y0,x1,y1=ROI
    trees={(x,y) for x in (23,30,38) for y in (18,38)}
    tree_right={(x+1,y) for x,y in trees}
    for x,y in trees | tree_right:
        assert (original[y,x]&1023) in (1,289)
        assert chunk['terrain'][(y+32)*128+x+64] == 1
    for y in range(y0,y1):
        for x in range(x0,x1):
            old=int(original[y,x]); old_id=old&1023
            # The roof ridge and plane live above the old ROI. Do not extend
            # landscaping/roads into these rows or roof over walkable cells.
            if y < 12 and not (old_id == 521 and 22 <= x <= 38):
                continue
            kind=chunk['terrain'][(y+32)*128+x+64]
            if old_id==521: symbol=_building_symbol(x,y,original)
            elif kind==5: symbol='tram'
            elif kind==4: symbol='road'
            elif kind==6:
                # Sparse local variation, coordinate-pinned to the immutable
                # GIS plaza mask. No banding or inferred route across cells.
                motif=(x*17+y*29+x*y*3)%13
                symbol='square_warm' if motif==2 else ('square_cool' if motif==7 else 'square')
            elif kind==3: symbol='path'
            elif kind==1 and old_id in (1,289):
                symbol=('tree_bed_l' if (x,y) in trees else
                        'tree_bed_r' if (x,y) in tree_right else 'green')
            else: symbol='unknown'
            west[y,x]=(old&0xfc00)|TILE_IDS[symbol]
    if np.any((west&0xfc00)!=(original&0xfc00)):
        raise ValueError('Collision/elevation changed')
    for name,data in (('Oberreut',west.astype('<u2').tobytes()),('OberreutOst',east)):
        folder=output/name; folder.mkdir(parents=True,exist_ok=True)
        (folder/'map.bin').write_bytes(data)
    count,hardware=_tileset(root,output)
    manifest={'scope':'Julius-Leber-Platz west-map visual slice',
              'roi_xyxy':list(ROI),'cell_m':2,'cell_px':16,
              'utm_bounds_wsen':[453248+2*x0,5426112-2*y1,453248+2*x1,5426112-2*y0],
              'metatile_ids':TILE_IDS,'secondary_metatiles':count,
              'secondary_hardware_tiles':hardware,
              'source_west_sha256':hashlib.sha256((source/'Oberreut/map.bin').read_bytes()).hexdigest(),
              'source_east_sha256':hashlib.sha256(east).hexdigest(),
              'changed_visual_cells':int(np.count_nonzero((west&1023)!=(original&1023))),
              'changed_collision_cells':0,
              'art_note':'Original interpretation of 2014 plaza and 2005 tram references. Roof modules, balconies, doors, sparse paving and paired tree beds are pinned in phase12.py, illustrative and not surveyed; no new passage. Source code is authoritative for regeneration.'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'data/oberreut/phase12-derived')
    args=parser.parse_args()
    print(json.dumps(generate(args.root,args.output),indent=2))
