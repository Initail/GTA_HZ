"""Single source renderer owner for reconstructed deck shells and asphalt.

Named structures supply their exact support domains, while the original road
graph still owns movement. No planar road intersection is turned into an edge.
"""
import json,math
from pathlib import Path
import shapely
from shapely.geometry import Polygon,Point,LineString,shape
from hangzhou_surface import digest

class SourceDecks:
    def __init__(self,root,field,plan):
        self.inputs={};self.decks=[];self.road_masks={};self.concrete_masks={};self.assets=[]
        root=Path(root)
        def read_bound(spec,key):
            name=spec[key];expected=spec[key+'Sha256']
            if digest(root/name)!=expected:raise ValueError('Changed deck ownership source '+name)
            self.inputs[name]=expected;return json.loads((root/name).read_text())
        def asset(spec):
            name=spec['asset']
            if digest(root/name)!=spec['assetSha256']:raise ValueError('Changed actual supporting structure')
            self.inputs[name]=spec['assetSha256'];self.assets.append({'asset':name,'sha256':spec['assetSha256']})
        by={r['id']:r for r in field.levels['roads']};groups={}
        for spec in plan.get('sourceDecks',[]):
            data=read_bound(spec,'domainsFile');asset(spec)
            for row in data['domains']:
                if row['mode']!='road':continue
                domain=Polygon(row['polygonGame']);top=row['heightGame'];bottom=row['undersideYGame']
                if not domain.is_valid or domain.area<=0 or not math.isfinite(top+bottom) or bottom>=top:raise ValueError('Invalid source deck solid')
                roads=[r for r in by.values() if any(r['id'].startswith(way+'#') for way in row['sourceWayIds'])]
                if not roads or any(r['tier']<=0 for r in roads):raise ValueError('Named bridge deck needs original elevated source road identities')
                # Source profile must already match the separately built rigid
                # structure. Closest XZ chooses only among its declared ways.
                probes=[*list(domain.exterior.coords)[:-1],list(domain.centroid.coords)[0]]
                for x,z in probes:
                    choices=[]
                    for r in roads:
                        for a,b,ya,yb in zip(r['points'],r['points'][1:],r['heights'],r['heights'][1:]):
                            dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz or 1)))
                            choices.append((math.hypot(x-a[0]-dx*t,z-a[1]-dz*t),ya+(yb-ya)*t))
                    if abs(min(choices)[1]-top)>.001:raise ValueError('Rigid deck/source profile mismatch '+row['id'])
                for r in roads:self.road_masks.setdefault(r['id'],[]).append(domain)
                key=(row['bridgeId'],top,bottom);groups.setdefault(key,[]).append(domain)
        for key,domains in groups.items():
            self.decks.append({'bridgeId':key[0],'top':key[1],'bottom':key[2],'geometry':shapely.union_all(domains)})
        for spec in plan.get('concreteReplacements',[]):
            data=read_bound(spec,'ownershipFile');asset(spec)
            for row in data['upperSourceOwnership']:
                rid=row['sourceRoadId']
                if rid not in by or by[rid]['tier']<=0:raise ValueError('Concrete replacement needs explicit upper road')
                self.concrete_masks.setdefault(rid,[]).append(shape(row['replaceConcreteDomain']))
        self.road_masks={k:shapely.union_all(v) for k,v in self.road_masks.items()}
        self.concrete_masks={k:shapely.union_all(v) for k,v in self.concrete_masks.items()}

    def ribbon_outside(self,road_id,geometry):
        owned=self.road_masks.get(road_id)
        return geometry.difference(owned) if owned is not None else geometry

    def concrete_outside(self,road_id,geometry):
        owned=self.concrete_masks.get(road_id)
        return geometry.difference(owned) if owned is not None else geometry

    def report(self):
        return {'deckGroups':len(self.decks),'sourceRoadIds':sorted(self.road_masks),'concreteReplacementRoadIds':sorted(self.concrete_masks),'requiredActualAssets':self.assets,'sourceWayCoordinatesAndTopologyModified':False,'pending':['actual serialized shell joints and body clearance','generic source widths beyond reported bridge footprint remain explicit uncertainty','whole-city browser rendering']}
