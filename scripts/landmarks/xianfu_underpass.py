"""Frozen-source Xianfu retaining-wall / overhead-deck candidate.

Pure import: no bpy/city_mesh, scene initialization or output writes. Geometry
is already game ENU, not metres awaiting a second .60 scale. The producer binds
source TIN, original source profiles and every estimated structural dimension.
It never emits another lower road floor. Main integration owns export/runtime.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,math
from pathlib import Path

def _edge(a,b):return tuple(sorted((tuple(a),tuple(b))))

def closed_shell(plan_triangles,top_at,bottom_at):
    """Closed oriented triangular shell using identical XY at top and bottom.

    Call once per continuous source-owned height region. Adjacent regions may
    have different real source profiles; do not average them into new floors.
    """
    plan=[tuple(tuple(map(float,p)) for p in t) for t in plan_triangles]
    counts=Counter(_edge(t[i],t[(i+1)%3]) for t in plan for i in range(3))
    if any(n not in (1,2) for n in counts.values()):raise ValueError('Nonmanifold planar region')
    vertices={p for t in plan for p in t};top={p:(*p,float(top_at(*p))) for p in vertices};bottom={p:(*p,float(bottom_at(*p))) for p in vertices}
    if any(top[p][2]<=bottom[p][2] for p in vertices):raise ValueError('Nonpositive structural thickness')
    faces=[]
    for t in plan:
        a,b,c=t
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<=0:raise ValueError('Plan triangles must be CCW')
        faces.append([top[p] for p in t]);faces.append([bottom[p] for p in reversed(t)])
        for i,p in enumerate(t):
            q=t[(i+1)%3]
            if counts[_edge(p,q)]==1:faces.extend([[bottom[p],bottom[q],top[q]],[bottom[p],top[q],top[p]]])
    return faces

def load_geometry(spec):
    if spec.get('cityId')!='hangzhou' or spec.get('units')!='game east/north/up; scale applied once':raise ValueError('Explicit Hangzhou game ENU spec required')
    root=Path(__file__).resolve().parents[2];p=(root/spec['geometryFile']).resolve();raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec['geometrySha256']:raise ValueError('Changed structural candidate geometry')
    d=json.loads(raw)
    if d['kind']!='xianfu-underpass-structure-candidate-v1':raise ValueError('Wrong structural geometry kind')
    return d

def projected_uv(triangle,origin):
    """Dominant-plane UVs, retaining world texture phase in small local values.

    Each planar face has one dominant projection; wall corners may change it.
    Integer texture-period subtraction preserves repeat coordinates exactly.
    """
    a,b,c=triangle;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    drop=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=drop]
    periods=[math.floor(origin[i]/8) for i in axes]
    return [tuple(p[i]/8-periods[j] for j,i in enumerate(axes)) for p in triangle]

def build_local(b,spec):
    """Recommended export: local ENU, caller applies returned origin once."""
    d=load_geometry(spec);origin=d['localOriginENU'];old=b.frame;b.frame=(0,0,0)
    try:
        for part in d['parts']:
            for t in part['trianglesENU']:
                points=[[v[i]-origin[i] for i in range(3)] for v in t]
                # World-space facade UVs remain stable when exported locally.
                uv=projected_uv(t,origin)
                b.face(part['material'],points,uv)
    finally:b.frame=old
    return {'originENU':origin,'scaleAlreadyApplied':True,'parts':len(d['parts'])}

def build(b,lm,spec,scale=.6):
    """Compatibility B API in world ENU; prefer build_local for float32 export.

    scale is deliberately NOT multiplied: source geometry is already game units.
    lm does not re-anchor this fixed source object. Its game origin is in spec.
    """
    if abs(float(scale)-.6)>1e-12:raise ValueError('Unexpected city scale contract')
    d=load_geometry(spec);old=b.frame;b.frame=(0,0,0)
    try:
        for part in d['parts']:
            for t in part['trianglesENU']:b.face(part['material'],t,projected_uv(t,d['localOriginENU']))
    finally:b.frame=old
    return {'worldENU':True,'noLowerRoadFloorEmitted':True}
