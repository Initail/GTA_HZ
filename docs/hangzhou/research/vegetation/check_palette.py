"""CPU budget, closed-face and silhouette regressions of local tree prototypes."""
import ast,copy,hashlib,importlib.util,json,math,sys
from collections import Counter
from pathlib import Path
from PIL import Image,ImageDraw
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'scripts'))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cross(p,q):return p[1]*q[2]-p[2]*q[1],p[2]*q[0]-p[0]*q[2],p[0]*q[1]-p[1]*q[0]
def area3(ps):
    a=ps[0];return sum(math.sqrt(sum(v*v for v in cross(tuple(x-y for x,y in zip(ps[i],a)),tuple(x-y for x,y in zip(ps[i+1],a)))))/2 for i in range(1,len(ps)-1))

def weld_safety(faces):
    """Guard B.finish's10µm material-local weld without importing Blender.

    Quantized points are a conservative regression guard, not an implementation
    of Blender's spatial weld. Every face and each triangle of its simple fan
    must remain nonzero; no same-material face may merely reverse another.
    """
    seen=set()
    for mat,ps in faces:
        qs=[tuple(round(v/1e-5) for v in p) for p in ps]
        assert len(set(qs))==len(qs),('coincident face vertices after10µm quantization',mat)
        assert all(math.dist(p,q)>1e-5 for i,p in enumerate(ps) for q in ps[i+1:]),('face edge collapsed by10µm distance weld',mat)
        key=(mat,tuple(sorted(qs)))
        assert key not in seen,('duplicate face regardless of winding',mat)
        seen.add(key)
        assert all(area3([ps[0],ps[i],ps[i+1]])>1e-10 for i in range(1,len(ps)-1)),('zero fan triangle',mat)

def closed_fan_leaves(mod,spec):
    t,xy,z,bare=mod._geometry(spec['prototype'],spec['lod'],spec['season'])
    faces=[ps for _,ps,part in t.faces if part=='ginkgo-fan-leaf-detail']
    if not faces:return
    edges=Counter();signed=Counter()
    for ps in faces:
        qs=[tuple(round(v*factor*.6/1e-5) for v,factor in zip(p,(xy,xy,z))) for p in ps]
        for p,q in zip(qs,qs[1:]+qs[:1]):
            edge=tuple(sorted((p,q)));edges[edge]+=1;signed[edge]+=1 if p<q else -1
    assert all(n==2 for n in edges.values()),'fan leaf boundary/nonmanifold edge'
    assert all(n==0 for n in signed.values()),'fan leaf winding mismatch'
    assert sum(len(ps)-2 for ps in faces)==12*24,'twelve closed fan leaves expected'

class Collector:
    def __init__(self,fault=False):self.frame=(13,19,.5);self.faces=[];self.fault=fault
    def face(self,m,ps):
        if self.fault:raise RuntimeError('injected collector fault')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((m,[(p[0]*c-p[1]*s+x,p[0]*s+p[1]*c+y,p[2]) for p in ps]))

def silhouette(faces,angle,height,radius):
    image=Image.new('1',(160,160));draw=ImageDraw.Draw(image)
    points=[]
    for _,ps in faces:
        p=[(80+(x*math.cos(angle)+y*math.sin(angle))/radius*70,147-z/height*135) for x,y,z in ps]
        draw.polygon(p,fill=1)
    return image

def iou(a,b):
    flatten=lambda im:list(im.get_flattened_data()) if hasattr(im,'get_flattened_data') else list(im.getdata())
    aa,bb=flatten(a),flatten(b);union=sum(bool(x or y) for x,y in zip(aa,bb));return sum(bool(x and y) for x,y in zip(aa,bb))/union

def main():
    path=ROOT/'scripts/landmarks/hangzhou_tree_palette.py';ref=importlib.util.spec_from_file_location('hztrees',path);mod=importlib.util.module_from_spec(ref);ref.loader.exec_module(mod)
    palette=json.loads((HERE/'palette-spec.json').read_text());evidence=json.loads((HERE/'evidence.json').read_text())
    for p,expected in evidence['sourceSnapshots'].items():assert sha(ROOT/p)==expected
    assert sha(HERE/'palette-spec.json')==evidence['paletteSpecSha256']
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n,ast.Import):assert all(a.name not in ('bpy','city_mesh','scripts.city_mesh') for a in n.names)
        if isinstance(n,ast.ImportFrom):assert n.module not in ('bpy','city_mesh','scripts.city_mesh')
    results=[];angles=[i*math.pi/8 for i in range(8)];archetypes={};seasons=[]
    for sp in palette['species']:
        sets=[];counts=[]
        for lod in range(3):
            spec=json.loads((HERE/f'prototype-specs/{sp["id"]}-lod{lod}.json').read_text());c=Collector();before=c.frame;report=mod.build(c,{'x':0,'z':0,'y':0},spec,.6)
            assert c.frame==before
            assert report['triangles']==sum(len(ps)-2 for _,ps in c.faces)<=spec['budget']['maxTriangles']
            assert len(report['materials'])<=spec['budget']['maxMaterials']
            assert all(area3(ps)>1e-10 for _,ps in c.faces),('degenerate face',sp['id'],lod)
            weld_safety(c.faces);closed_fan_leaves(mod,spec)
            assert math.isclose(report['heightGame'],sp['prototypeHeightM']*.6,abs_tol=1e-8)
            assert math.isclose(report['crownRadiusGame'],sp['prototypeCrownRadiusM']*.6,abs_tol=1e-8)
            assert report['newTextures']==report['newLights']==report['alphaCards']==0 and not report['geographicInventoryGenerated']
            d=Collector();mod.build(d,{'x':3,'z':5,'y':7},spec,.6)
            assert all(math.isclose(q[k]-p[k],delta,abs_tol=1e-8) for (_,ps),(_,qs) in zip(c.faces,d.faces) for p,q in zip(ps,qs) for k,delta in enumerate((3,5,7)))
            again=Collector();mod.build(again,{'x':0,'z':0,'y':0},spec,.6);assert again.faces==c.faces
            # Material definitions may change colour but never geometry/facecount.
            custom=copy.deepcopy(spec);custom['materialMap']={k:v['name'] for k,v in mod.material_definitions().items()}
            changed=Collector();creport=mod.build(changed,{'x':0,'z':0,'y':0},custom,.6)
            assert [ps for _,ps in c.faces]==[ps for _,ps in changed.faces] and creport['triangles']==report['triangles']
            sets.append(c.faces);counts.append(report['triangles']);results.append(report)
        assert counts[0]>counts[1]>counts[2],('LOD budget order',sp['id'],counts)
        similarity=[]
        for a in angles:
            masks=[silhouette(f,a,sp['prototypeHeightM']*.6,sp['prototypeCrownRadiusM']*.6) for f in sets]
            similarity.append({'yawRadians':a,'fullVsMidIoU':iou(masks[0],masks[1]),'fullVsFarIoU':iou(masks[0],masks[2])})
        assert min(m['fullVsMidIoU'] for m in similarity)>.72,(sp['id'],'mid silhouette loss',similarity)
        assert min(m['fullVsFarIoU'] for m in similarity)>.72,(sp['id'],'far silhouette loss',similarity)
        archetypes[sp['id']]={'triangles':counts,'silhouetteEightViews':similarity,'heightGame':sp['prototypeHeightM']*.6,'crownRadiusGame':sp['prototypeCrownRadiusM']*.6}
        for season in ('spring','autumn','winter'):
            spec=json.loads((HERE/f'prototype-specs/{sp["id"]}-lod0.json').read_text());spec['season']=season;c=Collector();r=mod.build(c,{'x':0,'z':0,'y':0},spec,.6)
            assert all(area3(ps)>1e-10 for _,ps in c.faces)
            weld_safety(c.faces);closed_fan_leaves(mod,spec)
            assert r['bareWinterAssetVariant']==(season=='winter' and sp['leafHabit']=='deciduous')
            if r['bareWinterAssetVariant']:assert not any('crown' in k for k in r['partTriangles'])
            seasons.append({'species':sp['id'],'season':season,'triangles':r['triangles'],'bareWinter':r['bareWinterAssetVariant']})
    fault=Collector(True);old=fault.frame
    try:mod.build(fault,{'x':0,'z':0,'y':0},spec,.6);raise AssertionError('swallowed receiver fault')
    except RuntimeError:assert fault.frame==old
    # Bad scale must fail rather than silently create different prototype units.
    try:mod.build(Collector(),{'x':0,'z':0,'y':0},spec,1);raise AssertionError('unscaled prototype accepted')
    except ValueError:pass
    # Distinct bounding aspect ratio/pendents/umbrella structure is recorded for
    # each species; mask comparisons are CPU geometry, not botanical accuracy.
    result={'date':'2026-10-14','sourceModuleSha256':sha(path),'paletteSpecSha256':sha(HERE/'palette-spec.json'),
        'scope':'CPU localprototype checks, not final botanical/game visual/collision/performance acceptance',
        'checks':{'sourceSnapshotsFrozen':True,'noSceneImports':True,'24LODBudgets':True,'geometryFiniteAndFacesNonzero':True,
            'dimensionsScaledOnceToGameUnits':True,'gameAnchorYNotRescaled':True,'deterministicMesh':True,'materialSlotsDoNotChangeGeometry':True,
            'materialLocalFacesNoReverseDuplicatesOr10umCoincidentVertices':True,'fanTrianglesNonzero':True,'ginkgoFanLeavesClosedAndConsistentlyWound':True,
            'LODCountsStrictlyDecrease':True,'LODEightViewSilhouetteEnvelopes':True,'staticSeasonVariantsRespectLeafHabits':True,
            'frameRestoration':True,'rejectSecondUnitConvention':True,'noInventoryOrSourcePhotoAssets':True},
        'models':results,'species':archetypes,'seasonVariants':seasons,'totalTrianglesAll24':sum(r['triangles'] for r in results),
        'glbs':[],'realGameScreenshots':[],'pending':palette['pendingSubscopes']}
    (HERE/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'CPUchecks':len(result['checks']),'24TotalTriangles':result['totalTrianglesAll24'],'perSpeciesTriangles':{k:v['triangles'] for k,v in archetypes.items()},'sourceModuleSha256':sha(path)}))

if __name__=='__main__':main()
