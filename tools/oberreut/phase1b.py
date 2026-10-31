#!/usr/bin/env python3
"""Phase 1.1b: exact-area building policy on the pinned Phase 1.1 ROI.

Only native metatile 0x209 and collision bits are updated; no OSM pedestrian
line is converted into an entrance or a verified rail crossing.
"""
import argparse
import hashlib
import json
import struct
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely import contains_xy
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import transform, unary_union
from shapely.prepared import prep

from generate_map import EXPECTED
from phase1_map import CHUNK_SHA256, source_geometry

X0, Y0, W, H = 453248, 5426112, 128, 64
ROI = box(X0, Y0 - H * 2, X0 + W * 2, Y0)
BUILDING_TILE = 0x209


def choose_buildings(area, small):
    """Per-cell analytic XOR optimum, subject to retaining every tiny footprint.

    Small entries are (OSM ID, polygon, iterable of positive-overlap (y,x,area)
    or (y,x) cells). Never select a zero-overlap cell for a small building.
    """
    result = area > 2  # strict tie: avoid adding solid terrain at exact half-area
    for identifier, polygon, cells in small:
        if any(result[y, x] for y, x, *rest in cells):
            continue
        eligible = [(float(area[y, x]) if not rest else rest[0], y, x)
                    for y, x, *rest in cells if area[y, x] > 0]
        if eligible:
            _, y, x = max(eligible)
            result[y, x] = True
    return result


def _geometry(feature, project):
    points = feature.get('geometry')
    if not points or len(points) < 2:
        return None
    xy = [project(p['lon'], p['lat']) for p in points]
    if len(xy) >= 4 and xy[0] == xy[-1]:
        p = Polygon(xy)
        return p if p.is_valid else p.buffer(0)
    return LineString(xy)


def _components(walk, start=(28, 30)):
    visited = np.zeros_like(walk, dtype=bool)
    if not walk[start]:
        return visited
    queue = deque([start]); visited[start] = True
    while queue:
        y, x = queue.popleft()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < H and 0 <= xx < W and walk[yy, xx] and not visited[yy, xx]:
                visited[yy, xx] = True; queue.append((yy, xx))
    return visited


def _collision_cause(y, x, building, terrain):
    if x in (0, W-1) or y in (0, H-1):
        return 'outer_perimeter'
    if building[y, x]:
        return 'building'
    if terrain[y, x] == 8:
        return 'water'
    return 'other_source_collision'


def _bottlenecks(walk, area, pedestrian_cells, tram, building, terrain):
    result = []
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            if not walk[y, x]:
                continue
            ns = not walk[y - 1, x] and not walk[y + 1, x]
            ew = not walk[y, x - 1] and not walk[y, x + 1]
            if not (ns or ew):
                continue
            result.append({'cell_xy': [x, y], 'utm_bounds_wsen': [X0 + x*2, Y0-(y+1)*2, X0+(x+1)*2, Y0-y*2],
                           'blocked_axis': ('NS' if ns else '') + ('EW' if ew else ''),
                           'blocked_neighbours': [
                               {'cell_xy': [xx, yy], 'cause': _collision_cause(yy, xx, building, terrain)}
                               for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)) if not walk[yy,xx]],
                           'building_overlap_m2': round(float(area[y, x]), 6),
                           'pedestrian_way_ids': sorted(pedestrian_cells.get((y, x), [])),
                           'tram_symbol': bool(tram[y, x])})
    return result


def generate(root: Path, output: Path):
    root = Path(root); output = Path(output)
    source = root / 'data/oberreut'
    # source_geometry validates both source hashes and the official boundary coverage.
    meta, roi, union, _ = source_geometry(root)
    assert roi.equals(ROI)
    for name, digest in CHUNK_SHA256.items():
        assert hashlib.sha256((source/'chunks'/name).read_bytes()).hexdigest() == digest
    project = Transformer.from_crs(4326, 25832, always_xy=True).transform
    osm = json.loads((source/'osm.json').read_text())['elements']
    polygons, pedestrian = [], []
    for feature in osm:
        g = _geometry(feature, project)
        if g is None or not g.intersects(ROI):
            continue
        tags = feature.get('tags', {})
        identifier = f"{feature['type']}/{feature['id']}"
        if tags.get('building') not in (None, 'no') and g.geom_type in ('Polygon', 'MultiPolygon'):
            p = g.intersection(ROI)
            if p.area > 0:
                polygons.append((identifier, p))
        if tags.get('highway') in ('footway','path','steps','pedestrian','living_street'):
            pedestrian.append((identifier, tags.get('highway'), g.intersection(ROI)))
    # Same polygon union and ROI as Phase 1.1; reject silent geometry drift.
    assert abs(union.area - unary_union([p for _, p in polygons]).area) < 1e-5
    chunks = [json.loads((source/f'chunks/{cx}_1.json').read_text()) for cx in (0, 1)]
    terrain = np.array([[chunks[(x+64)//128]['terrain'][(y+32)*128 + (x+64)%128]
                         for x in range(W)] for y in range(H)], dtype=np.uint8)
    blocked = np.array([[chunks[(x+64)//128]['blocked'][(y+32)*128 + (x+64)%128]
                         for x in range(W)] for y in range(H)], dtype=bool)
    old = terrain == 7
    prior = np.concatenate([np.frombuffer((source/'phase1-derived'/name/'map.bin').read_bytes(), dtype='<u2').reshape(64,64)
                            for name in ('Oberreut','OberreutOst')], axis=1).copy()
    assert np.array_equal((prior & 1023) == BUILDING_TILE, old)
    old_solid = (prior & 0xc00) != 0
    prepared = prep(union)
    area = np.zeros((H, W), dtype=float)
    cells = {}
    for y in range(H):
        for x in range(W):
            cell = box(X0+x*2, Y0-(y+1)*2, X0+(x+1)*2, Y0-y*2)
            cells[y, x] = cell
            if prepared.intersects(cell):
                area[y, x] = union.intersection(cell).area
    small = []
    all_building_ids = []
    for identifier, polygon in polygons:
        all_building_ids.append(identifier)
        bounds = polygon.bounds
        lowx=max(0,int((bounds[0]-X0)//2)); highx=min(W-1,int((bounds[2]-X0)//2))
        lowy=max(0,int((Y0-bounds[3])//2)); highy=min(H-1,int((Y0-bounds[1])//2))
        overlaps = [(y,x,polygon.intersection(cells[y,x]).area)
                    for y in range(lowy,highy+1) for x in range(lowx,highx+1)
                    if polygon.intersects(cells[y,x]) and polygon.intersection(cells[y,x]).area > 1e-10]
        small.append((identifier,polygon,overlaps))
    xs = X0 + (np.arange(W)+.5)*2
    ys = Y0 - (np.arange(H)+.5)*2
    xx, yy = np.meshgrid(xs, ys)
    centre = contains_xy(union,xx,yy)
    hybrid = choose_buildings(area, small)
    # Never open a previously blocked cell simply because a raster building was
    # corrected. The underlying surface/access is not known from this dataset.
    new_solid = old_solid | (hybrid & ~old)
    updated = prior.copy()
    updated[hybrid & ~old] = (updated[hybrid & ~old] & 0xfc00) | BUILDING_TILE | 0xc00
    updated[old & ~hybrid] = (updated[old & ~hybrid] & 0xfc00) | 0x121 | 0xc00
    assert np.array_equal((updated & 0xc00) != 0, new_solid)
    # No other features, events, map connections or gameplay code are edited.
    output.mkdir(parents=True, exist_ok=True)
    for name, sl in (('Oberreut', slice(0,64)), ('OberreutOst',slice(64,128))):
        dest = output/name; dest.mkdir(exist_ok=True)
        (dest/'map.bin').write_bytes(updated[:,sl].astype('<u2').tobytes())
    by_way = []
    way_cells = {}
    for identifier, highway, geom in pedestrian:
        lines = list(geom.geoms) if geom.geom_type in ('MultiLineString','GeometryCollection') else [geom]
        points = []
        for line in lines:
            if line.geom_type != 'LineString' or not line.length:
                continue
            for distance in np.arange(0,line.length+.001,.5):
                p = line.interpolate(min(distance,line.length))
                x=int((p.x-X0)//2); y=int((Y0-p.y)//2)
                if 0<=x<W and 0<=y<H:
                    points.append((y,x)); way_cells.setdefault((y,x),set()).add(identifier)
        reason = Counter()
        for y,x in points:
            if old_solid[y,x]:
                reason[_collision_cause(y,x,old,terrain)] += 1
        by_way.append({'way':identifier, 'highway':highway, 'samples':len(points),
                       'blocked_samples':sum(reason.values()), 'causes':dict(sorted(reason.items())),
                       'new_blocked_samples':sum(bool(new_solid[y,x]) for y,x in points),
                       'newly_blocked_samples':sum(bool(new_solid[y,x] and not old_solid[y,x]) for y,x in points)})
    by_way.sort(key=lambda entry:(-entry['blocked_samples'],entry['way']))
    assert sum(row['samples'] for row in by_way)==4675
    assert sum(row['blocked_samples'] for row in by_way)==625
    old_walk = ~old_solid; new_walk = ~new_solid
    old_reach = _components(old_walk); new_reach = _components(new_walk)
    old_narrow = _bottlenecks(old_walk,area,way_cells,terrain==5,old,terrain)
    new_narrow = _bottlenecks(new_walk,area,way_cells,terrain==5,hybrid,terrain)
    assert len(old_narrow)==34
    def measure(mask):
        return {'cells':int(mask.sum()), 'analytic_xor_m2':float(np.where(mask,4-area,area).sum()),
                'only_vector_m2':float(area[~mask].sum()), 'only_cells_m2':float((4-area[mask]).sum())}
    per_way = [{'way':identifier,'clipped_area_m2':polygon.area,
                'old_cells':sum(bool(old[y,x]) for y,x,*_ in overlaps),
                'hybrid_cells':sum(bool(hybrid[y,x]) for y,x,*_ in overlaps)}
               for identifier,polygon,overlaps in small]
    lost = [r['way'] for r in per_way if r['clipped_area_m2'] < 4 and not r['hybrid_cells']]
    all_lost = [r['way'] for r in per_way if not r['hybrid_cells']]
    assert not all_lost
    report = {'scope':{'crs':'EPSG:25832','bounds_wsen':[453248,5425984,453504,5426112],
                       'cell_m':2,'grid_wh':[128,64],'source_sha256':EXPECTED,
                       'chunk_sha256':CHUNK_SHA256,'reference':'OSM snapshot, not an independent survey'},
              'buildings':{'vector_area_m2':union.area,'old':measure(old),'centre':measure(centre),
                           'hybrid':measure(hybrid),'changed_cells':int((hybrid^old).sum()),
                           'newly_building_cells':int((hybrid&~old).sum()),
                           'removed_building_cells':int((old&~hybrid).sum()),
                           'small_buildings_under_4m2':sum(r['clipped_area_m2'] < 4 for r in per_way),
                           'small_buildings_lost':lost,'building_ways_lost':all_lost,
                           'per_way':per_way,'building_way_count':len(all_building_ids),
                           'policy':'exact union intersection > 2 m2 per 4 m2 cell; retain each clipped tiny building via greatest positive overlap; keep old collision when deleting old building symbols'},
              'footways':{'old':{'samples':4675,'blocked_samples':625},
                          'new':{'samples':sum(r['samples'] for r in by_way),
                                 'blocked_samples':sum(r['new_blocked_samples'] for r in by_way),
                                 'newly_blocked_samples':sum(r['newly_blocked_samples'] for r in by_way)},
                          'by_way':by_way,
                          'note':'0.5 m centreline samples, repeated cells and endpoints; blocked is a raster observation, not a legal-access classification'},
              'bottlenecks':{'old':old_narrow,'new':new_narrow,
                             'note':'One-cell open candidates with opposite blocked neighbours; no verified physical width or safe tram crossing'},
              'connectivity':{'old_spawn_reachable_cells':int(old_reach.sum()),
                              'new_spawn_reachable_cells':int(new_reach.sum()),
                              'new_seam_reachable_rows':[y for y in range(H) if new_reach[y,63] and new_reach[y,64]],
                              'newly_open_cells':int((new_walk&~old_walk).sum())}}
    assert report['connectivity']['newly_open_cells'] == 0
    assert report['connectivity']['new_seam_reachable_rows'], 'Lost all west/east transitions'
    # Two registered 512x256 panels: left old, right new, 0.5 m/pixel.
    # Red: building only before; blue: building only after; grey: unchanged.
    canvas=Image.new('RGB',(1024,310),(246,244,235))
    for index, mask in enumerate((old,hybrid)):
        array=np.empty((H,W,3),dtype=np.uint8);array[:]=(230,227,215)
        array[mask]=(64,65,64)
        array[mask & old & ~hybrid]=(220,65,55)
        array[mask & hybrid & ~old]=(47,87,211)
        image=Image.fromarray(array,'RGB').resize((512,256),Image.Resampling.NEAREST)
        draw=ImageDraw.Draw(image)
        draw.line((256,0,256,256),fill=(239,36,214),width=2)
        canvas.paste(image,(index*512,54))
    draw=ImageDraw.Draw(canvas)
    draw.text((6,5),'BEFORE: Phase 1.1   |   AFTER: Phase 1.1b   EPSG:25832',fill=(0,0,0))
    draw.text((6,26),'E 453248..453504 N 5425984..5426112 | 0.5 m/px | red removed; blue added; magenta seam',fill=(0,0,0))
    canvas.save(output/'before-after-registered.png')
    (output/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'data/oberreut/phase1b-derived')
    args=parser.parse_args()
    print(json.dumps(generate(args.root,args.output)['buildings'],indent=2))
