"""Partition render domains before sampling source-owned site height fields.

Each returned piece owns its boundary height. Sampling the global field at a
cut boundary would pull the outside mesh down and invent a sloping bank.
This module does not invent tunnel roofs or convert floor edges into roads.
"""
from dataclasses import dataclass
from typing import Callable
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree

def polygon_parts(g):
    if g.geom_type == 'Polygon':
        if not g.is_empty and g.area > 0:yield g
    else:
        for child in getattr(g,'geoms',[]):yield from polygon_parts(child)

def plane(triangle):
    a,b,c=triangle
    det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    if det<=0:raise ValueError('Source plane must face upward')
    def sample(x,z):
        dx,dz=x-a[0],z-a[1]
        u=(dx*(c[1]-a[1])-dz*(c[0]-a[0]))/det
        v=((b[0]-a[0])*dz-(b[1]-a[1])*dx)/det
        return a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])
    return sample

@dataclass
class Piece:
    shape: object
    height: Callable
    owners: tuple

class SitePartition:
    def __init__(self,data):
        self.layers={}
        for kind in ('terrainPatches','terrainCuts'):
            entries=[]
            for group in data.get(kind,[]):
                if any(any(e) for e in group.get('openEdges',[])):
                    raise ValueError('Terrain render partition requires closed source faces')
                for i,t in enumerate(group['triangles']):
                    entries.append((Polygon([p[:2] for p in t]),plane(t),group['id']+':'+str(i)))
            self.layers[kind]=(entries,STRtree([e[0] for e in entries]))
        entries,tree=self.layers['terrainPatches']
        for i,(boundary,_,_) in enumerate(entries):
            for j in tree.query(boundary,predicate='intersects'):
                if j>i and boundary.intersection(entries[int(j)][0]).area>0:
                    raise ValueError('Source patch interiors overlap')

    def split(self,shape,base):
        """Return disjoint interiors covering the supplied polygon exactly.

        Patches replace uncut earth; cuts take min with the current piece.
        Shared edges may be present in both closures with distinct heights.
        The caller must close those vertical discontinuities explicitly.
        """
        entries,tree=self.layers['terrainPatches'];pieces=[];owned=[]
        for i in sorted(tree.query(shape,predicate='intersects')):
            boundary,height,owner=entries[int(i)]
            inside=boundary if shape.covers(boundary) else shape.intersection(boundary)
            for p in polygon_parts(inside):
                pieces.append(Piece(p,height,(owner,)));owned.append(p)
        pieces.extend(Piece(p,base,()) for p in polygon_parts(shape.difference(shapely.union_all(owned))))
        for kind in ('terrainCuts',):
            entries,tree=self.layers[kind]
            for i in sorted(tree.query(shape,predicate='intersects')):
                boundary,height,owner=entries[int(i)];result=[]
                for part in pieces:
                    if not part.shape.intersects(boundary):result.append(part);continue
                    inside=part.shape.intersection(boundary)
                    if inside.area==0:result.append(part);continue
                    # Preserve exact source vertices if the complete triangle
                    # is owned. In particular, do not discard tiny TIN faces.
                    if part.shape.covers(boundary):inside=boundary
                    result.extend(Piece(p,part.height,part.owners) for p in polygon_parts(part.shape.difference(boundary)))
                    next_height=lambda x,z,h=height,old=part.height:min(old(x,z),h(x,z))
                    result.extend(Piece(p,next_height,part.owners+(owner,)) for p in polygon_parts(inside))
                pieces=result
        return pieces

def triangulate_piece(piece):
    """Keep every positive-area constrained triangle; no area decimation."""
    for t in polygon_parts(shapely.constrained_delaunay_triangles(piece.shape)):
        ps=list(t.exterior.coords)[:3]
        if not t.exterior.is_ccw:ps.reverse()
        yield [[x,z,piece.height(x,z)] for x,z in ps]
