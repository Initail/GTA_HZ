"""Pure FakeB checks; not GLB, Blender, art fidelity or game acceptance."""
from pathlib import Path
import importlib.util
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


class FakeB:
    def __init__(self,fail_at=None):self.frame=(17,29,.34);self.faces=[];self.fail_at=fail_at
    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)==self.fail_at:raise RuntimeError('test interruption')
        x,y,angle=self.frame;c,s=math.cos(angle),math.sin(angle)
        self.faces.append((mat,[(u*c-v*s+x,u*s+v*c+y,z) for u,v,z in points]))


def area(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    q=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    return math.sqrt(sum(x*x for x in q))/2


def main():
    source=ROOT/'scripts/landmarks/wulin_square.py'
    loader=importlib.util.spec_from_file_location('wulin_candidate',source)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    assert 'bpy' not in sys.modules and 'city_mesh' not in sys.modules
    spec=json.loads((HERE/'spec.json').read_text());city=load_city('hangzhou');a=spec['anchor'];xy=project(a['lon'],a['lat'],city)
    lm={'lon':a['lon'],'lat':a['lat'],'x':xy[0],'z':xy[1],'y':2.5}
    b=FakeB();result=module.build(b,lm,spec)
    assert b.frame==(17,29,.34)
    points=[p for _,f in b.faces for p in f]
    assert all(math.isfinite(v) for p in points for v in p)
    assert result['centralDancerCount']==3 and result['outerMusicianCount']==5 and result['poolPetalCount']==5
    expected_top=(spec['estimates']['raisedPoolHeightM']['value']+spec['estimates']['centralGroupHeightM']['value'])*.6+lm['y']
    assert abs(max(p[2] for p in points)-expected_top)<1e-8
    assert min(p[2] for p in points)>=lm['y']
    count=sum(len(f)-2 for _,f in b.faces)
    assert count==result['triangleCountBeforeExport']<=25000
    assert len(set(mat for mat,_ in b.faces))==len(result['materials'])<=12
    bad=[(idx,i) for idx,(_,f) in enumerate(b.faces) for i in range(1,len(f)-1) if area(f[0],f[i],f[i+1])<1e-10]
    assert not bad, f'Degenerate triangle fans {bad[:8]}'
    mapped=[project(*p,city) for p in spec['footprintWGS84'][:-1]];actual=module.plaza_outline(lm,spec)
    assert all(min(math.dist(p,q) for q in actual)<1e-8 for p in mapped)
    # The exact concave map polygon is triangulated, without a fan filling
    # outside the western notch. Compare total source area against mesh faces.
    measurement=json.loads((HERE/'measurements.json').read_text())
    paving_area=sum(area(f[0],f[1],f[2]) for mat,f in b.faces if mat=='pavement')
    assert abs(paving_area-measurement['mappedAreaM2']*.6**2)<1e-5
    half=FakeB();module.build(half,lm,spec,scale=.3)
    assert half.frame==b.frame and len(half.faces)==len(b.faces)
    for (_,f),(_,g) in zip(b.faces,half.faces):
        for p,q in zip(f,g):
            for i,origin in enumerate((lm['x'],lm['z'],lm['y'])):assert abs((p[i]-origin)/2-(q[i]-origin))<1e-8
    interrupted=FakeB(fail_at=3)
    try:module.build(interrupted,lm,spec);raise AssertionError('interruption not reached')
    except RuntimeError as error:assert str(error)=='test interruption'
    assert interrupted.frame==(17,29,.34)
    shifted=dict(lm,lon=lm['lon']+.0001,lat=lm['lat']-.0001);shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city)
    shifted_outline=module.plaza_outline(shifted,spec)
    assert all(min(math.dist(p,q) for q in shifted_outline)<1e-8 for p in mapped)
    collision=module.ground_footprints(lm,spec)
    assert len(collision)==1 and len(collision[0])==100
    # Collision candidate encloses the fountain; the whole open plaza is not
    # returned as an impassable building envelope. Physics acceptance pending.
    result.update({'checks':{'finiteVertices':True,'noDegenerateTriangleFans':True,'threePlusFiveSculptureRoles':True,
                            'exactMappedPlazaProjection':True,'concavePavingAreaAgreement':True,
                            'frameRestoredOnSuccessAndFailure':True,'oneTimeScaleAndGameBasePreserved':True,
                            'sourceAnchoringWithShiftedLm':True,'trianglesMaterialsWithinCpuBudget':True,
                            'noSceneImports':True,'collisionEnvelopeLimitedToFountain':True},
                   'sourceModuleSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                   'specSha256':hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest(),
                   'boundsGameENU':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},
                   'validationScope':'Pure FakeB B-face primitive record only; not actual Blender triangulation/GLB, sculpture fidelity, current visual, physics, shader, browser, night or FPS acceptance'})
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
