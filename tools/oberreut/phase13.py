#!/usr/bin/env python3
"""Julius-Leber-Platz visual refinement over the immutable Phase 1.2 baseline.

OSM lines locate platforms/tracks; material, architectural and tree drawings
are original interpretations. No new passage, footprint or collision changes.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import LineString, Point

import phase12 as base
from phase1_map import source_geometry

ROI = base.ROI
EXTRA = ('grass_a', 'grass_b', 'grass_c', 'square_band',
         'square_edge_n', 'square_edge_s', 'square_edge_w', 'square_edge_e',
         'ballast', 'platform_w', 'platform_e', 'stop_sign',
         'canopy_l', 'canopy_r', 'trunk_l', 'trunk_r',
         'path_curb_w', 'path_curb_e')
KINDS = base.KINDS + EXTRA
TILE_IDS = {kind: 656 + i for i, kind in enumerate(KINDS)}
PLATFORM_WAYS = (35995211, 35995212)
TRACK_WAYS = (138293860, 138293880)


def art(kind):
    if kind in ('canopy_l', 'canopy_r', 'trunk_l', 'trunk_r'):
        # One 32x32 crown and round bed, split into four hardware metatiles.
        pair = Image.new('P', (32,32), 11)
        d = ImageDraw.Draw(pair)
        d.ellipse((1,22,30,31), fill=3)
        d.ellipse((2,22,29,29), fill=5)
        d.ellipse((4,22,27,28), fill=10)
        d.rectangle((14,13,17,26),fill=9)
        d.line((14,15,14,25),fill=7)
        d.ellipse((2,5,30,22),fill=10)
        d.ellipse((3,2,27,19),fill=10)
        for box in ((4,3,17,14),(12,1,25,12),(15,8,29,17),(6,11,18,20)):
            d.ellipse(box,fill=11)
        for box in ((6,4,14,9),(15,2,22,7),(19,10,25,13),(8,12,13,15)):
            d.ellipse(box,fill=12)
        for x,y in ((8,4),(19,3),(12,12),(23,10)):
            d.point((x,y), fill=6)  # restrained chestnut blossom highlights
        x=0 if kind.endswith('_l') else 16
        y=0 if kind.startswith('canopy') else 16
        return pair.crop((x,y,x+16,y+16))
    if kind.startswith('grass') or kind == 'green':
        im=Image.new('P',(16,16),11);d=ImageDraw.Draw(im)
        points={'grass_a':((3,10),(12,3)), 'grass_b':((8,6),),
                'grass_c':((2,2),(11,13)), 'green':()}[kind]
        for x,y in points:
            d.line((x,y,x+2,y),fill=10);d.point((x+1,y-1),fill=12)
        return im
    if kind.startswith('square'):
        im=Image.new('P',(16,16),5);d=ImageDraw.Draw(im)
        # Small subdued concrete pavers, with joints continuous across variants.
        for y in (3,7,11,15):
            d.line((0,y,15,y),fill=4)
        for row in range(4):
            for x in ((3,11) if row%2 else (7,15)):
                d.line((x,row*4,x,row*4+2),fill=4)
        if kind == 'square_warm':d.line((1,4,5,4),fill=6)
        if kind == 'square_cool':d.line((9,12,13,12),fill=3)
        if kind == 'square_band':
            d.rectangle((0,6,15,9),fill=3)
            d.line((0,6,15,6),fill=4)
        if kind.startswith('square_edge'):
            side=kind[-1]
            box={'n':(0,0,15,2),'s':(0,13,15,15),'w':(0,0,2,15),'e':(13,0,15,15)}[side]
            d.rectangle(box,fill=3)
        return im
    if kind in ('tram','ballast'):
        im=Image.new('P',(16,16),3);d=ImageDraw.Draw(im)
        for x,y in ((1,3),(8,6),(14,1),(4,12),(12,14)):d.point((x,y),fill=2)
        if kind=='tram':
            for y in (3,11):d.rectangle((1,y,14,y+1),fill=8)
            for x in (4,11):
                d.line((x,0,x,15),fill=1);d.line((x+1,0,x+1,15),fill=5)
        return im
    if kind.startswith('platform') or kind=='stop_sign':
        im=Image.new('P',(16,16),4);d=ImageDraw.Draw(im)
        d.line((0,7,15,7),fill=3);d.line((7,0,7,15),fill=3)
        x=1 if kind=='platform_w' else 12
        d.rectangle((x,0,x+2,15),fill=6)
        for y in range(1,16,3):d.point((x+1,y),fill=3)
        if kind=='stop_sign':
            d.line((7,5,7,15),fill=2)
            d.rectangle((2,0,11,9),fill=10);d.rectangle((3,1,10,8),fill=15)
            d.line((5,2,5,6),fill=10);d.line((8,2,8,6),fill=10);d.line((5,4,8,4),fill=10)
        return im
    if kind in ('path','path_curb_w','path_curb_e'):
        im=Image.new('P',(16,16),4);d=ImageDraw.Draw(im)
        d.line((0,7,15,7),fill=3);d.line((7,0,7,6),fill=3);d.line((3,8,3,15),fill=3)
        if kind!='path':
            x=0 if kind.endswith('_w') else 14
            d.rectangle((x,0,x+1,15),fill=5)
        return im
    if kind in ('roof_ridge','roof_plane','roof_eave','roof_end_l','roof_end_r'):
        im=Image.new('P',(16,16),2);d=ImageDraw.Draw(im)
        for y in (3,7,11,15):
            d.line((0,y,15,y),fill=3)
            for x in (3,11):d.point((x,y-1),fill=1)
        if kind=='roof_ridge':d.rectangle((0,0,15,2),fill=3);d.line((0,3,15,3),fill=1)
        if kind=='roof_eave':d.line((0,13,15,13),fill=5);d.rectangle((0,14,15,15),fill=1)
        if kind.startswith('roof_end'):
            x=0 if kind.endswith('_l') else 15;d.line((x,0,x,15),fill=1)
        return im
    im=base._art(kind)
    d=ImageDraw.Draw(im)
    if kind in ('wall_window','wall_base_window'):
        d.rectangle((4,4,11,11),fill=1);d.rectangle((5,5,10,10),fill=3)
        d.line((5,5,7,5),fill=6);d.line((8,4,8,11),fill=5)
        d.line((3,12,12,12),fill=5);d.line((3,13,12,13),fill=2)
    if kind in ('wall_base','wall_base_window','wall_entrance'):
        d.rectangle((0,14,15,15),fill=4)
        if kind=='wall_entrance':d.line((3,14,12,14),fill=2)
    if kind=='balcony_rail':
        d.rectangle((0,14,15,15),fill=2);d.line((0,13,15,13),fill=5)
    return im


def geometry(root):
    # Validate archived OSM, boundary and raster hashes before using geometry.
    source_geometry(root)
    transform=Transformer.from_crs(4326,25832,always_xy=True)
    elements={e['id']:e for e in json.loads((root/'data/oberreut/osm.json').read_text())['elements'] if e['type']=='way'}
    result={}
    for ident in PLATFORM_WAYS+TRACK_WAYS:
        feature=elements[ident]
        assert feature['tags']['railway'] in ('platform','tram')
        result[ident]=LineString([((east-453248)/2,(5426112-north)/2)
            for east,north in [transform.transform(p['lon'],p['lat']) for p in feature['geometry']]])
    return result


def generate(root,output):
    root=Path(root);output=Path(output)
    source=root/'data/oberreut/phase12-derived'
    before=np.frombuffer((source/'Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    west=before.copy()
    original=np.frombuffer((root/'data/oberreut/phase1b-derived/Oberreut/map.bin').read_bytes(),dtype='<u2').reshape(64,64)
    terrain=np.array(json.loads((root/'data/oberreut/chunks/0_1.json').read_text())['terrain']).reshape(128,128)[32:96,64:128]
    lines=geometry(root)
    x0,y0,x1,y1=ROI
    platforms=[];rails=[]
    for y in range(y0,y1):
        for x in range(x0,x1):
            old=int(original[y,x])&1023;kind=terrain[y,x];symbol=None
            if y<12 or old==521:continue
            if kind==1 and old in (1,289):
                motif=(x*19+y*31+x*y)%11
                symbol=('grass_a','grass_b','grass_c')[motif%3] if motif<3 else 'green'
            elif kind==6:
                for dx,dy,suffix in ((0,-1,'n'),(0,1,'s'),(-1,0,'w'),(1,0,'e')):
                    if terrain[y+dy,x+dx]!=6:
                        symbol='square_edge_'+suffix;break
                # Reference photograph shows dark transverse paving inlays;
                # these row positions are explicitly artistic, not surveyed.
                if symbol is None and y in (25,33):symbol='square_band'
            elif kind==5:
                scan=LineString([(x0,y+0.5),(x1,y+0.5)])
                track_cols={math.floor(p.x) for ident in TRACK_WAYS
                            for p in [lines[ident].intersection(scan)] if isinstance(p,Point)}
                symbol='tram' if x in track_cols else 'ballast'
                if symbol=='tram':rails.append([x,y])
            elif kind==3:
                if terrain[y,x-1]==4:symbol='path_curb_w'
                elif terrain[y,x+1]==4:symbol='path_curb_e'
            # OSM platforms are lines, not surveyed-width polygons. Only the
            # containing 2m cell is styled, excluding rails and buildings.
            if kind not in (4,5) and old!=521:
                for ident in PLATFORM_WAYS:
                    p=lines[ident].intersection(LineString([(x0,y+0.5),(x1,y+0.5)]))
                    if isinstance(p,Point) and math.floor(p.x)==x:
                        symbol='platform_e' if ident==35995212 else 'platform_w'
                        if ident==35995212 and y==20:symbol='stop_sign'
                        platforms.append({'xy':[x,y],'osm_way':ident})
            if symbol:west[y,x]=(int(before[y,x])&0xfc00)|TILE_IDS[symbol]
    # Six existing paired tree beds become larger crowns; all four cells must
    # remain inside the baseline green mask. Twelve real trees are not claimed.
    for x in (23,30,38):
        for y in (17,38):
            for dx,dy,symbol in ((0,0,'canopy_l'),(1,0,'canopy_r'),(0,1,'trunk_l'),(1,1,'trunk_r')):
                assert terrain[y+dy,x+dx]==1 and (original[y+dy,x+dx]&1023) in (1,289)
                west[y+dy,x+dx]=(int(before[y+dy,x+dx])&0xfc00)|TILE_IDS[symbol]
    assert np.array_equal(west&0xfc00,before&0xfc00)
    output.mkdir(parents=True,exist_ok=True)
    for name,data in (('Oberreut',west.astype('<u2').tobytes()),('OberreutOst',(source/'OberreutOst/map.bin').read_bytes())):
        folder=output/name;folder.mkdir(exist_ok=True);(folder/'map.bin').write_bytes(data)
    # Preserve all upstream bytes; redraw only original art in palette bank 6.
    stock=root/'data/tilesets/secondary/petalburg'
    atlas=Image.new('P',(128,80+math.ceil(len(KINDS)/8)*16),0)
    atlas.putpalette([v for rgb in base.COLORS for v in rgb]+[0]*(768-48))
    atlas.paste(Image.open(stock/'tiles.png'),(0,0))
    entries=[]
    for i,kind in enumerate(KINDS):
        atlas.paste(art(kind),((i%8)*16,80+(i//8)*16))
        tx=(i%8)*2;ty=10+(i//8)*2
        entries.extend([0x6000+512+(ty+dy)*16+tx+dx for dy,dx in ((0,0),(0,1),(1,0),(1,1))]+[0]*4)
    assert atlas.width*atlas.height//64<=512 and max(TILE_IDS.values())<1024
    atlas.save(output/'tiles.png')
    (output/'metatiles.bin').write_bytes((stock/'metatiles.bin').read_bytes()+struct.pack('<'+'H'*len(entries),*entries))
    (output/'metatile_attributes.bin').write_bytes((stock/'metatile_attributes.bin').read_bytes()+bytes(2*len(KINDS)))
    (output/'palettes').mkdir(exist_ok=True)
    for p in (source/'palettes').glob('*.pal'):(output/'palettes'/p.name).write_bytes(p.read_bytes())
    report={'phase':'1.3','roi_xyxy':list(ROI),'changed_collision_cells':0,
            'changed_visual_cells':int(np.count_nonzero(west!=before)),
            'source_west_sha256':hashlib.sha256(before.tobytes()).hexdigest(),
            'platform_cells':platforms,'rail_cells':rails,'metatile_ids':TILE_IDS,
            'secondary_hardware_tiles':atlas.width*atlas.height//64,
            'secondary_metatiles':max(TILE_IDS.values())-511,
            'interpretations':['six symbolic tree beds; not all twelve real trees',
              '2m cells approximate OSM platform lines without asserted width',
              'facade/roof modules, paving inlays and stop icon are illustrative'],
            'references':['OSM archived ways 35995211,35995212,138293860,138293880,4940191',
              'https://stadtlexikon.karlsruhe.de/index.php/De:Lexikon:top-1414']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(generate(args.root,args.output),indent=2))
