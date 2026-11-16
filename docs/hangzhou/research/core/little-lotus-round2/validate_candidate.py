"""Actual pure FakeB contract check; no Blender, GLB, game or visual claim."""
from pathlib import Path
import importlib.util
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


class FakeB:
    def __init__(self,fail_at=None):self.frame=(17,29,.34);self.faces=[];self.fail_at=fail_at
    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)==self.fail_at:raise RuntimeError('test interruption')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((mat,[(u*c-v*s+x,u*s+v*c+y,z) for u,v,z in points]))


def area(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    q=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);return math.sqrt(sum(x*x for x in q))/2


def main():
    path=ROOT/'scripts/landmarks/little_lotus.py';loader=importlib.util.spec_from_file_location('little_lotus_candidate',path)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    assert 'bpy' not in sys.modules and 'city_mesh' not in sys.modules
    spec=json.loads((HERE/'spec.json').read_text());city=load_city('hangzhou');a=spec['anchor'];xy=project(a['lon'],a['lat'],city)
    lm={'lon':a['lon'],'lat':a['lat'],'x':xy[0],'z':xy[1],'y':2.5}
    b=FakeB();result=module.build(b,lm,spec)
    assert b.frame==(17,29,.34)
    assert result['fixedPetalCount']==24 and result['upperPetalCount']==8
    assert result['roofState']=='open-static' and result['roofAnimationImplemented'] is False
    assert result['upperPetalMinimumPlanRadiusM']>=spec['estimates']['openingRadiusM']['value']-.26
    points=[p for _,f in b.faces for p in f]
    assert all(math.isfinite(v) for p in points for v in p)
    assert abs(min(p[2] for p in points)-lm['y'])<1e-8
    assert abs(max(p[2] for p in points)-(spec['estimates']['candidateHeightM']['value']*.6+lm['y']))<1e-8
    bad=[(idx,i) for idx,(_,f) in enumerate(b.faces) for i in range(1,len(f)-1) if area(f[0],f[i],f[i+1])<1e-10]
    assert not bad, f'Degenerate triangle fans: {bad[:8]}'
    count=sum(len(f)-2 for _,f in b.faces)
    assert count==result['triangleCountBeforeExport']<=25000
    assert len({mat for mat,_ in b.faces})==len(result['materials'])<=12
    mapped=[project(*p,city) for p in spec['footprintWGS84'][:-1]];actual=module.ground_footprints(lm,spec)[0]
    assert len(actual)==48 and all(min(math.dist(p,q) for q in actual)<1e-8 for p in mapped)
    half=FakeB();module.build(half,lm,spec,scale=.3)
    assert half.frame==b.frame and len(half.faces)==len(b.faces)
    for (_,f),(_,g) in zip(b.faces,half.faces):
        for p,q in zip(f,g):
            for i,o in enumerate((lm['x'],lm['z'],lm['y'])):assert abs((p[i]-o)/2-(q[i]-o))<1e-8
    interrupted=FakeB(fail_at=3)
    try:module.build(interrupted,lm,spec);raise AssertionError('interruption not reached')
    except RuntimeError as error:assert str(error)=='test interruption'
    assert interrupted.frame==(17,29,.34)
    shifted=dict(lm,lon=lm['lon']+.0001,lat=lm['lat']-.0001);shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city)
    moved=module.ground_footprints(shifted,spec)[0]
    assert all(min(math.dist(p,q) for q in moved)<1e-8 for p in mapped)
    assert spec['baseBuildingIdsToExclude']==['relation/9874418']
    result.update({'checks':{'finiteVertices':True,'noDegenerateTriangleFans':True,'mappedFootprintProjection':True,
                            'twentyFourPlusEightSeparateRoles':True,'staticOpenOnlyNoAnimationClaim':True,
                            'upperPanelsLeaveCentralOpening':True,'oneTimeScaleAndGameBasePreserved':True,
                            'frameRestoredOnSuccessAndFailure':True,'shiftedLmSourceAnchoring':True,
                            'cpuTrianglesMaterialsWithinBudget':True,'noSceneImports':True,'neighborNotExcluded':True},
                   'sourceModuleSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'specSha256':hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest(),
                   'boundsGameENU':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},
                   'validationScope':'Pure FakeB primitive recording only; not actual GLB/Blender triangulation, current visual/material, physics, browser, night, mechanical simulation or FPS acceptance'})
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
