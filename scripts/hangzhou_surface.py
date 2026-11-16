"""Pure game-unit sampler matching CityRoadLevels.groundAt (no bpy import)."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from functools import lru_cache
import numpy as np
from hangzhou_site_surfaces import SiteSurfaces

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class Surface:
    def __init__(self,root):
        self.root=Path(root);self.manifest=json.loads((self.root/'geography/manifest.json').read_text());m=self.manifest;self.grid=m['grid'];self.transition=m['roadTerrainTransitionGame'];self.cells={}
        if m['cityId']!='hangzhou' or m['units']!='game metres; scale applied once':raise ValueError('Hangzhou game-unit geography required')
        terrain=self.root/'geography'/m['terrainFile'];roads=self.root/'geography'/m['roadLevelsFile']
        if digest(terrain)!=m['terrainSha256'] or digest(roads)!=m['roadLevelsSha256']:raise ValueError('Changed physical source')
        self.sites=None
        if 'siteSurfacesFile' in m or 'siteSurfacesSha256' in m:
            site_file=self.root/'geography'/m['siteSurfacesFile']
            if digest(site_file)!=m['siteSurfacesSha256']:raise ValueError('Changed site surface source')
            self.sites=SiteSurfaces(json.loads(site_file.read_text()))
        g=self.grid;self.values=np.fromfile(terrain,dtype='<f4').reshape(g['rows'],g['columns']);self.levels=json.loads(roads.read_text())
        if not np.isfinite(self.values).all():raise ValueError('Incomplete terrain')
        for road in self.levels['roads']:
            if len(road['points'])!=len(road['heights']) or len(road['points'])!=len(road['nodeIds']):raise ValueError('Invalid source road surface')
            if road['tier']!=0:continue
            for i,(a,b) in enumerate(zip(road['points'],road['points'][1:])):
                margin=road['width']/2+self.transition;row=(a,b,road['heights'][i],road['heights'][i+1],road['width'])
                for x in range(math.floor((min(a[0],b[0])-margin)/100),math.floor((max(a[0],b[0])+margin)/100)+1):
                    for z in range(math.floor((min(a[1],b[1])-margin)/100),math.floor((max(a[1],b[1])+margin)/100)+1):self.cells.setdefault((x,z),[]).append(row)
    def terrain(self,x,z):
        g=self.grid;u=(x-g['x0'])/g['step'];v=(z-g['z0'])/g['step']
        if not math.isfinite(u) or not math.isfinite(v):return 0
        i,j=math.floor(u),math.floor(v)
        if not 0<=i<g['columns']-1 or not 0<=j<g['rows']-1:return 0
        fx,fz=u-i,v-j
        a,b,d,c=map(float,[self.values[j,i],self.values[j,i+1],self.values[j+1,i],self.values[j+1,i+1]])
        return a+(b-a)*fx+(d-a)*fz if fx+fz<=1 else c+(d-c)*(1-fx)+(b-c)*(1-fz)
    @lru_cache(maxsize=600000)
    def uncut_ground(self,x,z):
        if not math.isfinite(x+z):raise ValueError('Invalid ground query')
        weighted,total,influence=0.,0.,0.
        for a,b,ya,yb,width in self.cells.get((math.floor(x/100),math.floor(z/100)),[]):
            dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz or 1)));d=math.hypot(x-a[0]-dx*t,z-a[1]-dz*t)
            if d>=width/2+self.transition:continue
            edge=max(0,min(1,(d-width/2)/self.transition));weight=1-edge*edge*(3-2*edge)
            weighted+=(ya+(yb-ya)*t)*weight;total+=weight;influence=max(influence,weight)
        base=self.terrain(x,z)
        return base+(weighted/total-base)*influence if total>0 else base
    def ground(self,x,z):
        ground=self.uncut_ground(x,z)
        return self.sites.ground_at(x,z,ground) if self.sites else ground
