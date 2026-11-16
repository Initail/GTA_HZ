"""Preserve declared local-asset seam vertices/heights in adjacent terrain.

Only a finite boundary is overridden; this does not alter physical geography.
All intermediate points follow the actual asset's piecewise-linear edge.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Point,LineString,Polygon,MultiPolygon
from shapely.strtree import STRtree


class RenderSeams:
    def __init__(self, segments=()):
        self.segments=[];vertices={}
        for pair in segments:
            if len(pair)!=2 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in pair):raise ValueError('Invalid ENU seam')
            a,b=pair
            if math.dist(a[:2],b[:2])<=0:raise ValueError('Zero-length seam')
            self.segments.append(pair)
            for p in pair:
                key=tuple(p[:2])
                if key in vertices and abs(vertices[key]-p[2])>1e-6:raise ValueError('Conflicting shared seam height')
                vertices[key]=p[2]
        self.vertices=list(vertices);self.points=STRtree([Point(p) for p in self.vertices])
        self.lines=STRtree([LineString([p[:2] for p in pair]) for pair in self.segments])

    def height(self,x,z,fallback):
        values=[];point=Point(x,z)
        for index in self.lines.query(point,predicate='dwithin',distance=1e-9):
            a,b=self.segments[int(index)];dx,dz=b[0]-a[0],b[1]-a[1]
            t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/(dx*dx+dz*dz)))
            values.append(a[2]+t*(b[2]-a[2]))
        if not values:return fallback(x,z)
        if max(values)-min(values)>1e-6:raise ValueError('Conflicting intersecting seam height')
        return sum(values)/len(values)

    def pin(self,geometry):
        if geometry.is_empty or not self.vertices:return geometry
        if geometry.geom_type=='Polygon':
            def ring(coords):
                coords=list(coords);result=[]
                for a,b in zip(coords,coords[1:]):
                    result.append(a);dx,dz=b[0]-a[0],b[1]-a[1];length2=dx*dx+dz*dz
                    if length2==0:raise ValueError('Repeated boundary point')
                    extra=[]
                    for index in self.points.query(LineString([a,b]),predicate='dwithin',distance=1e-9):
                        p=self.vertices[int(index)];t=((p[0]-a[0])*dx+(p[1]-a[1])*dz)/length2
                        if 0<t<1 and math.dist(p,a)>1e-9 and math.dist(p,b)>1e-9:extra.append((t,p))
                    result.extend(p for _,p in sorted(extra));
                return result+[result[0]]
            result=Polygon(ring(geometry.exterior.coords),[ring(r.coords) for r in geometry.interiors])
            if not result.is_valid or not result.buffer(1e-9).covers(geometry) or not geometry.buffer(1e-9).covers(result):raise ValueError('Seam insertion changed terrain domain')
            return result
        if geometry.geom_type=='MultiPolygon':return MultiPolygon([self.pin(p) for p in geometry.geoms])
        return shapely.GeometryCollection([self.pin(p) for p in geometry.geoms]) if hasattr(geometry,'geoms') else geometry
