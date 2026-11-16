"""Source-owned exclusions for a full-city rebuild with local terrain assets.

Local GLBs replace these domains at assembly time; they are never overlays.
This preparation contract is not a seam, actor or visual acceptance result.
"""
import json
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, box, shape
from hangzhou_surface import digest
from hangzhou_render_seams import RenderSeams
from hangzhou_render_decks import SourceDecks


class SiteRender:
    def __init__(self, root, field, plan_path):
        self.inputs = {}
        self.patch_faces = []
        self.road_faces = []
        self.road_ids = set()
        self.road_domains = {}
        self.ground_road_domain=shapely.GeometryCollection()
        self.external = []
        self.excluded = shapely.GeometryCollection()
        self.patches = shapely.GeometryCollection()
        self.crops = shapely.GeometryCollection()
        self.render_owners = []
        self.seams = RenderSeams()
        self.decks = SourceDecks(root,field,{})
        if not field.sites:
            if plan_path: raise ValueError('A site plan requires source site surfaces')
            return
        if not plan_path: raise ValueError('Site geography requires an explicit render replacement plan')
        root = Path(root).resolve()
        plan_path = Path(plan_path).resolve()
        self.inputs[str(plan_path.relative_to(root))] = digest(plan_path)
        plan = json.loads(plan_path.read_text())
        if plan.get('schemaVersion') != 1 or plan.get('cityId') != 'hangzhou':
            raise ValueError('Invalid site render plan')
        if plan['geographyManifestSha256'] != digest(field.root/'geography/manifest.json'):
            raise ValueError('Render plan does not bind current geography')
        self.decks=SourceDecks(root,field,plan);self.inputs.update(self.decks.inputs)
        sites_path = (field.root/'geography'/field.manifest['siteSurfacesFile']).resolve()
        self.inputs[str(sites_path.relative_to(root))] = digest(sites_path)
        sites = json.loads(sites_path.read_text())
        for group in sites.get('terrainPatches', []):
            self.patch_faces.extend(group['triangles'])
        self.patches = shapely.union_all([Polygon([v[:2] for v in t]) for t in self.patch_faces])
        crop_shapes = [];seam_segments=[]
        def bound_json(name):
            if name not in self.inputs:raise ValueError('Unbound seam/ownership input '+name)
            return json.loads((root/name).read_text())
        for replacement in plan.get('terrainReplacements', []):
            # A rectangle makes crop ownership explicit and repeatable. Water
            # remains a separate source pipeline, even inside this rectangle.
            crop = box(*replacement['bboxGame'])
            if not crop.is_valid or crop.area <= 0: raise ValueError('Invalid terrain replacement crop')
            for previous in crop_shapes:
                if crop.intersection(previous).area > 0: raise ValueError('Overlapping terrain replacements')
            for name, expected in replacement['inputs'].items():
                path = root/name
                if digest(path) != expected: raise ValueError('Changed replacement input '+name)
                self.inputs[name] = expected
            asset = root/replacement['asset']
            if digest(asset) != replacement['assetSha256']: raise ValueError('Changed replacement GLB')
            self.inputs[replacement['asset']] = replacement['assetSha256']
            crop_shapes.append(crop)
            self.external.append(replacement)
            if replacement.get('boundaryFile'):
                boundary=bound_json(replacement['boundaryFile'])
                seam_segments.extend(row['enu'] for row in boundary['orderedSegments'])
        owner_shapes=[]
        for owner in plan.get('renderTerrainOwners', []):
            for name, expected in owner['inputs'].items():
                if digest(root/name)!=expected:raise ValueError('Changed render ownership input '+name)
                self.inputs[name]=expected
            if digest(root/owner['asset'])!=owner['assetSha256']:raise ValueError('Changed render owner GLB')
            self.inputs[owner['asset']]=owner['assetSha256']
            data=bound_json(owner['maskFile'])
            matches=[f for f in data['features'] if f.get('properties',{}).get('id')==owner['featureId']]
            if len(matches)!=1:raise ValueError('Ambiguous render ownership feature')
            geometry=shape(matches[0]['geometry'])
            if not geometry.is_valid or geometry.is_empty:raise ValueError('Invalid render ownership domain')
            owner_shapes.append(geometry);self.render_owners.append(owner)
            boundary=bound_json(owner['boundaryFile'])
            seam_segments.extend(row['enu'] for row in boundary['orderedSegments'])
        self.seams=RenderSeams(seam_segments)
        self.crops = shapely.union_all(crop_shapes)
        if self.crops.intersection(self.patches).area > 0:
            raise ValueError('Local asset and source TIN claim the same terrain')
        cuts = shapely.union_all([Polygon([v[:2] for v in t]) for g in sites.get('terrainCuts', []) for t in g['triangles']])
        if cuts.difference(self.crops).area > 0:
            raise ValueError('A terrain cut has no explicit local replacement')
        # A terrain cut must not silently lower an asphalt ribbon while the
        # source profile or connected ramp still uses its former elevation.
        # These ways need their own source-owned surface contract first.
        unowned_roads = []
        for road in field.levels['roads']:
            if road['tier'] != 0 or road.get('surfaceGroup'): continue
            footprint = LineString(road['points']).buffer(road['width']/2+1.8, cap_style=2, join_style=2)
            if not footprint.intersects(cuts): continue
            area = footprint.intersection(cuts).area
            if area > 0: unowned_roads.append((road['id'], area))
        if unowned_roads:
            raise ValueError('Ground road/pavement intersects a cut without source surface ownership: '+repr(unowned_roads))
        self.excluded = shapely.union_all([self.patches, self.crops,*owner_shapes])
        claimed = set();paired_faces=[];ground_domains=[]
        patches_by_id={group['id']:group['triangles'] for group in sites.get('terrainPatches',[])}
        road_only={entry['id']:entry for entry in plan.get('roadOnlySurfaces',[])}
        if len(road_only)!=len(plan.get('roadOnlySurfaces',[])):raise ValueError('Repeated road-only surface contract')
        used_road_only=set();levels_by_id={r['id']:r for r in field.levels['roads']}
        for group in sites.get('roadSurfaces', []):
            ids = set(group['roadIds'])
            if claimed.intersection(ids): raise ValueError('Two site surfaces claim a source road')
            claimed.update(ids)
            self.road_ids.update(ids)
            self.road_faces.extend(group['triangles'])
            group_domain=shapely.union_all([Polygon([v[:2] for v in t]) for t in group['triangles']])
            for rid in ids:self.road_domains[rid]=group_domain
            if group['id'] in patches_by_id:
                if not np.array_equal(np.asarray(group['triangles']),np.asarray(patches_by_id[group['id']])):raise ValueError('Source road and terrain TIN ordinates/order disagree')
                paired_faces.extend(group['triangles']);ground_domains.append(group_domain)
            else:
                if group['id'] not in road_only:raise ValueError('Unbound road-only surface')
                entry=road_only[group['id']];used_road_only.add(group['id'])
                if set(entry['roadIds'])!=ids:raise ValueError('Road-only source identity mismatch')
                if digest(root/entry['supportAsset'])!=entry['supportAssetSha256']:raise ValueError('Changed road-only supporting asset')
                self.inputs[entry['supportAsset']]=entry['supportAssetSha256']
                for rid in ids:
                    if rid not in levels_by_id or levels_by_id[rid].get('surfaceGroup')!=group['id']:raise ValueError('Road-only surface lacks physical source binding')
                if any(levels_by_id[rid]['tier']==0 for rid in ids):
                    raise ValueError('Road-only stacked surface requires an explicit physical tier; do not raise ground')
        if used_road_only!=set(road_only):raise ValueError('Unused road-only surface contract')
        self.ground_road_domain=shapely.union_all(ground_domains)
        road_domain = shapely.union_all([Polygon([v[:2] for v in t]) for t in paired_faces])
        if road_domain.symmetric_difference(self.patches).area > 0:
            raise ValueError('Source road and terrain TIN footprints disagree')
        # Preserve the exact source surfaces, including the very thin faces.
        if not np.array_equal(np.asarray(paired_faces), np.asarray(self.patch_faces)):
            raise ValueError('Source road and terrain TIN ordinates/order disagree')

    def terrain_outside(self, geometry):
        return geometry.difference(self.excluded) if geometry.intersects(self.excluded) else geometry

    def roads_outside(self, geometry,road_id=None):
        owned=self.ground_road_domain if road_id is None else self.road_domains.get(road_id,shapely.GeometryCollection())
        return geometry.difference(owned) if geometry.intersects(owned) else geometry

    def pin_geometry(self,geometry):
        return self.seams.pin(geometry)

    def terrain_height(self,x,z,fallback):
        return self.seams.height(x,z,fallback)

    def report(self):
        return {
            'sourceTerrainTriangles': len(self.patch_faces),
            'sourceAsphaltTriangles': len(self.road_faces),
            'roadIds': sorted(self.road_ids),
            'terrainExclusionAreaGame2': self.excluded.area,
            'terrainReplacements': self.external,
            'renderTerrainOwners': self.render_owners,
            'sharedSeamSegments':len(self.seams.segments),
            'sourceDecks':self.decks.report(),
            'assemblyRequired': bool(self.external or self.render_owners),
            'pending': ['local terrain assets must be merged exactly once',
                        'actual crop/TIN outer seams and tunnel structures',
                        'actual GLB and whole-city actor/browser checks'],
        }
