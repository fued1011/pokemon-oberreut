#!/usr/bin/env python3
"""Rebuild two native Emerald layouts and a projected OSM/GBA rasterization audit.

Original OSM and municipal boundary remain immutable. V1.2's 2 m raster is
used for terrain/collision; original projected OSM building geometry supplies
an independent, finer-sampled comparison, not a claim of positional accuracy.
"""
import argparse
import collections
import hashlib
import json
import struct
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor
from pyproj import Transformer
from shapely import contains_xy
from shapely.geometry import Polygon, shape, box
from shapely.ops import transform, unary_union

from generate_map import EXPECTED, METATILES

CROPS = {'Oberreut': (64, 160, 64, 64), 'OberreutOst': (128, 160, 64, 64)}
CHUNK_SHA256 = {'0_1.json': 'e86e43db6f610b1d9cb8dd697980addd8d8085decae379377175a8b194fc2093',
                '1_1.json': '0032b8b3b2795a0cc28f090c7b4d1048320027ea9c9bb72c09b09b0e7b6cff3a'}
# V1.2 code 1 is a default background, not evidence of mapped vegetation.
# Explicit OSM vegetation is independently projected and flagged in the audit.
COLORS = {0: '#1a2325', 1: '#528b5c', 2: '#aba589', 3: '#d3b98b',
          4: '#606b70', 5: '#a99775', 6: '#e3c59a', 7: '#a05c4b',
          8: '#45859a', 9: '#39734d'}


def source_geometry(root):
    source = root / 'data/oberreut'
    for name, expected in EXPECTED.items():
        actual = hashlib.sha256((source / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'GIS snapshot changed: {name}: {actual}')
    for name, expected in CHUNK_SHA256.items():
        actual = hashlib.sha256((source / 'chunks' / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Raster snapshot changed: {name}: {actual}')
    meta = json.loads((source / 'raster-metadata.json').read_text())
    if meta['source_sha256'] != EXPECTED or (meta['tile_m'], meta['tile_px']) != (2, 16):
        raise ValueError('Unexpected raster contract')
    transformer = Transformer.from_crs(4326, 25832, always_xy=True)
    boundary = transform(transformer.transform, shape(json.loads((source / 'boundary.geojson').read_text())['features'][0]['geometry']))
    roi = box(453120 + 64*2, 5426432 - 224*2, 453120 + 192*2, 5426432 - 160*2)
    if not boundary.covers(roi):
        raise ValueError('Map extends outside official Oberreut boundary')
    features = json.loads((source / 'osm.json').read_text())['elements']
    buildings, vegetation = [], []
    for feature in features:
        tags = feature.get('tags', {})
        building = 'building' in tags
        green = tags.get('landuse') in ('grass', 'forest', 'meadow', 'recreation_ground') or tags.get('natural') in ('wood', 'grassland', 'scrub') or tags.get('leisure') in ('park', 'garden')
        if not (building or green):
            continue
        coords = feature.get('geometry', [])
        if len(coords) < 4:
            continue
        coords = [(p['lon'], p['lat']) for p in coords]
        if coords[0] != coords[-1]:
            continue
        polygon = transform(transformer.transform, Polygon(coords))
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if not polygon.is_empty and polygon.intersects(roi):
            (buildings if building else vegetation).append(polygon.intersection(roi))
    return meta, roi, unary_union(buildings), unary_union(vegetation)


def generate(root: Path, output: Path) -> None:
    meta, roi, buildings, vegetation = source_geometry(root)
    source = root / 'data/oberreut'
    chunks = {int(p.stem.split('_')[0]): json.loads(p.read_text())
              for p in (source / 'chunks').glob('*_1.json')}
    for cx, chunk in chunks.items():
        if (chunk['cx'], chunk['cy']) != (cx, 1) or any(len(chunk[k]) != 16384 for k in ('terrain', 'blocked')):
            raise ValueError('Unexpected chunk shape')
    tiles_by_map = {}
    kinds_by_map = {}
    semantic_by_map = {}
    counts = collections.Counter()
    green_cells = 0
    unknown_cells = 0
    for name, (x0, y0, w, h) in CROPS.items():
        tiles, kinds, semantics = [], [], []
        for y in range(y0, y0+h):
            for x in range(x0, x0+w):
                chunk = chunks[x // 128]
                i = (y-128)*128 + x % 128
                kind = chunk['terrain'][i]
                if kind not in METATILES:
                    raise ValueError(f'Unknown terrain code {kind}')
                # Retain original V1.2 physics on the connected seam. The outer
                # perimeter alone is closed; the engine performs the map switch.
                solid = bool(chunk['blocked'][i]) or kind in (0, 8) or y in (160, 223) or x in (64, 191)
                semantic = kind
                metatile = METATILES[kind]
                if kind == 1:
                    e = meta['origin_easting'] + (x + 0.5)*2
                    n = meta['origin_northing'] - (y + 0.5)*2
                    if vegetation.covers(box(e, n, e, n)):
                        green_cells += 1
                    else:
                        unknown_cells += 1
                        semantic = 10  # Unclassified default, not mapped grass.
                        metatile = 0x121  # Neutral existing tile; no new artwork.
                tile = 0x3000 | (0xc00 if solid else 0) | metatile
                tiles.append(tile)
                kinds.append(kind)
                semantics.append(semantic)
                counts[meta['kinds'][kind]] += 1
        output_dir = output / name
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / 'map.bin').write_bytes(struct.pack('<4096H', *tiles))
        tiles_by_map[name] = tiles
        kinds_by_map[name] = kinds
        semantic_by_map[name] = semantics
    spawn = (int(meta['spawn']['x']) - 64, int(meta['spawn']['y']) - 160)
    if tiles_by_map['Oberreut'][spawn[1]*64+spawn[0]] & 0xc00:
        raise ValueError('Spawn blocked')
    # Native 4-neighbour path across map seam; no diagonals or teleportation.
    visited = {(94, 188)}
    queue = deque(visited)
    def passable(x, y):
        if not 64 <= x < 192 or not 160 <= y < 224:
            return False
        name = 'Oberreut' if x < 128 else 'OberreutOst'
        return not tiles_by_map[name][(y-160)*64 + (x % 64)] & 0xc00
    while queue:
        x, y = queue.popleft()
        for point in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if point not in visited and passable(*point):
                visited.add(point)
                queue.append(point)
    reachable_maps = [name for name, (x, _, _, _) in CROPS.items() if any(x <= a < x+64 for a, b in visited)]
    # A genuinely finer reference grid, projected from original OSM footprints.
    step = 0.5
    xs = 453248 + (np.arange(512) + .5)*step
    ys = 5426112 - (np.arange(256) + .5)*step
    xx, yy = np.meshgrid(xs, ys)
    original_mask = contains_xy(buildings, xx, yy)
    game_mask = np.array([[kinds_by_map['Oberreut' if x < 64 else 'OberreutOst'][y*64+x%64] == 7
                           for x in range(128)] for y in range(64)])
    sampled_game = np.repeat(np.repeat(game_mask, 4, axis=0), 4, axis=1)
    symmetric = np.count_nonzero(original_mask != sampled_game) * step * step
    # Comparison panels: original OSM building mask, GBA raster, overlay error.
    image = Image.new('RGB', (1536, 256), '#ffffff')
    original = Image.fromarray(np.where(original_mask, 40, 235).astype('uint8'), 'L').convert('RGB')
    gba = Image.fromarray(np.where(sampled_game, 40, 235).astype('uint8'), 'L').convert('RGB')
    overlay = np.full((256, 512, 3), 235, dtype=np.uint8)
    overlay[original_mask & sampled_game] = (40, 40, 40)
    overlay[original_mask & ~sampled_game] = (216, 45, 45)
    overlay[~original_mask & sampled_game] = (40, 90, 210)
    image.paste(original, (0, 0)); image.paste(gba, (512, 0)); image.paste(Image.fromarray(overlay), (1024, 0))
    output.mkdir(parents=True, exist_ok=True)
    image.save(output / 'gis-gba-comparison.png')
    colors = {**COLORS, 10: '#8a8b7c'}
    semantic_preview = Image.new('RGB', (128, 64))
    semantic_preview.putdata([ImageColor.getrgb(colors[semantic_by_map['Oberreut' if x < 64 else 'OberreutOst'][y*64+x%64]])
                              for y in range(64) for x in range(128)])
    semantic_preview.resize((1024, 512), Image.Resampling.NEAREST).save(output / 'semantic-preview.png')
    reference_names = {}
    reference_ids = {}
    for ref in meta['references']:
        entry = {'osm_id': ref['osm_id'], 'osm_type': ref['type'], 'global_cell': [ref['x'], ref['y']],
                                         'map': 'Oberreut' if ref['x'] < 128 else 'OberreutOst',
                                         'easting': ref['easting'], 'northing': ref['northing']}
        reference_names[ref['name']] = entry
        reference_ids[f"{ref['type']}/{ref['osm_id']}"] = entry
    manifest = {'crs': meta['crs'], 'origin_easting': meta['origin_easting'],
                'origin_northing': meta['origin_northing'], 'metres_per_cell': 2,
                'pixels_per_cell': 16, 'source_sha256': EXPECTED,
                'raster_chunk_sha256': CHUNK_SHA256,
                'maps': {name: {'crop': list(crop), 'utm_bounds': [453120+crop[0]*2, 5426432-(crop[1]+64)*2, 453120+(crop[0]+64)*2, 5426432-crop[1]*2]} for name, crop in CROPS.items()},
                'spawn': {'map': 'Oberreut', 'local_cell': list(spawn), 'global_cell': [94,188]},
                'references': reference_names,
                'references_by_osm_id': reference_ids,
                'terrain_counts': dict(sorted(counts.items())),
                'background_classification': {'explicit_osm_green_centres': green_cells, 'unclassified_default_centres': unknown_cells,
                                              'warning': 'Only OSM-tagged vegetation is painted green. Unclassified V1.2 background uses neutral paving as a visual placeholder; original V1.2 walkability retained and is NOT verified pedestrian access.'},
                'reachability': {'reachable_maps': reachable_maps, 'reachable_cells': len(visited),
                                 'east_seam_reachable_rows': sorted(y-160 for x,y in visited if x == 128 and (127,y) in visited)},
                'metrics': {'buildings': {'reference_polygon_area_m2': round(buildings.area, 2),
                                          'reference_sampled_area_m2': round(float(original_mask.sum())*step*step, 2),
                                          'gba_raster_area_m2': int(game_mask.sum())*4,
                                          'sampled_symmetric_difference_m2': round(symmetric, 2),
                                          'reference_sampling_m': step,
                                          'method': 'OSM polygon union clipped to ROI; 0.5 m centre samples against V1.2 2 m building cells; rasterization error, not absolute accuracy'}}}
    (output / 'phase1-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] / 'data/oberreut/phase1-derived')
    args = parser.parse_args()
    generate(args.root, args.output)
