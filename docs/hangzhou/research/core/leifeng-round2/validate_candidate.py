"""CPU B recorder: projection, one-time scale, budget and primitive validity.

Does not import bpy/city_mesh, launch Blender, export GLB or open the game.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


class FakeB:
    def __init__(self,fail_at=None):
        self.frame=(17,29,.34)
        self.faces=[]
        self.fail_at=fail_at

    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)==self.fail_at:
            raise RuntimeError('test interruption')
        x,y,angle=self.frame
        c,s=math.cos(angle),math.sin(angle)
        self.faces.append((mat,[(u*c-v*s+x,u*s+v*c+y,z) for u,v,z in points]))


def area(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    q=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    return math.sqrt(sum(x*x for x in q))/2


def main():
    path=ROOT/'scripts/landmarks/leifeng_pagoda.py'
    loader=importlib.util.spec_from_file_location('leifeng_candidate',path)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    assert 'bpy' not in sys.modules and 'city_mesh' not in sys.modules
    spec=json.loads((HERE/'spec.json').read_text())
    city=load_city('hangzhou');a=spec['anchor']
    xy=project(a['lon'],a['lat'],city)
    lm={'lon':a['lon'],'lat':a['lat'],'x':xy[0],'z':xy[1],'y':2.5}
    b=FakeB();result=module.build(b,lm,spec)
    assert b.frame==(17,29,.34)
    points=[p for _,f in b.faces for p in f]
    assert all(math.isfinite(v) for p in points for v in p)
    assert abs(min(p[2] for p in points)-lm['y'])<1e-9
    assert abs(max(p[2] for p in points)-(71*.6+2.5))<1e-9
    count=sum(len(f)-2 for _,f in b.faces)
    assert count==result['triangleCountBeforeExport']<25000
    assert len({mat for mat,_ in b.faces})==len(result['materials'])<=12
    bad=[(idx,i) for idx,(_,f) in enumerate(b.faces) for i in range(1,len(f)-1) if area(f[0],f[i],f[i+1])<1e-10]
    assert not bad, f'Degenerate triangle fans: {bad[:8]}'
    mapped=[project(*p,city) for p in spec['base']['footprintWGS84'][:-1]]
    footprint=module.ground_footprints(lm,spec)[0]
    assert len(footprint)==8
    assert all(min(math.dist(p,q) for q in footprint)<1e-8 for p in mapped)
    # Build the very same source geometry at half scale, anchored in game units.
    half=FakeB();module.build(half,lm,spec,scale=.3)
    assert half.frame==b.frame
    assert len(half.faces)==len(b.faces)
    for (_,f),(_,g) in zip(b.faces,half.faces):
        for p,q in zip(f,g):
            assert abs((p[0]-lm['x'])/2-(q[0]-lm['x']))<1e-8
            assert abs((p[1]-lm['z'])/2-(q[1]-lm['z']))<1e-8
            assert abs((p[2]-lm['y'])/2-(q[2]-lm['y']))<1e-8
    interrupted=FakeB(fail_at=3)
    try:
        module.build(interrupted,lm,spec)
        raise AssertionError('injected interruption was not reached')
    except RuntimeError as error:
        assert str(error)=='test interruption'
    assert interrupted.frame==(17,29,.34)
    # Verify footprint remains tied to source position when lm anchor is nearby.
    shifted=dict(lm,lon=lm['lon']+.0001,lat=lm['lat']-.0001)
    shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city)
    footprint_shifted=module.ground_footprints(shifted,spec)[0]
    assert all(min(math.dist(p,q) for q in footprint_shifted)<1e-8 for p in mapped)
    result.update({'checks':{'finiteVertices':True,'noDegenerateTriangleFans':True,'sharedHangzhouProjectionAgreement':True,
                           'frameRestoredOnSuccessAndFailure':True,'geometryScaledOnceAndBaseNotScaled':True,
                           'sourceAnchoringWithShiftedLm':True,'trianglesAndMaterialsWithinCpuBudget':True,
                           'importHasNoSceneModules':True},
                   'sourceModuleSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'specSha256':hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest(),
                   'validationScope':'CPU FakeB primitive geometry only; no actual GLB, Blender mesh triangulation, visual, collision, shader, browser or FPS result',
                   'boundsGameENU':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}})
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
