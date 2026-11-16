"""Rebuild labelled orthographic CPU previews; these are not runtime screenshots."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0,str(ROOT/'scripts'))


def load(name,path):
    ref = importlib.util.spec_from_file_location(name,path)
    mod = importlib.util.module_from_spec(ref)
    ref.loader.exec_module(mod)
    return mod


def dot(p,q):
    return sum(a*b for a,b in zip(p,q))


def norm(p):
    length = math.sqrt(dot(p,p))
    return tuple(v/length for v in p)


def cross(p,q):
    return p[1]*q[2]-p[2]*q[1],p[2]*q[0]-p[0]*q[2],p[0]*q[1]-p[1]*q[0]


def main():
    spec = json.loads((HERE/'spec.json').read_text())
    checker = load('candidate_checker',HERE/'check_candidate.py')
    mod = load('alibaba_a_candidate',ROOT/'scripts/landmarks/alibaba_a.py')
    collector = checker.Collector()
    lm = {'x':0,'z':0,'y':0,'lon':spec['anchor']['lon'],'lat':spec['anchor']['lat']}
    report = mod.build(collector,lm,spec,1)
    palette = {'concrete':(153,160,158),'darkglass':(32,52,64),'gold':(153,99,47),
               'landmarkglass':(85,123,139),'roof':(121,128,132),'silver':(195,204,207),'steel':(97,117,123)}
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',25)
    small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
    images = []
    isolated = []
    first = last = 0
    for part,triangles in report['partTriangles'].items():
        last += triangles
        if part == 'link-6752593':
            subtotal = 0
            for mat,pts in collector.faces:
                end = subtotal+len(pts)-2
                if first <= subtotal and end <= last:
                    isolated.append((mat,pts))
                subtotal = end
        first = last
    for name,direction in [('top',(0,0,1)),('southeast',(1,-1,.85)),('south',(0,-1,.15)),('link-6752593-close',(0,-1,.30))]:
        faces = isolated if name.startswith('link-') else collector.faces
        view = norm(direction)
        right = (1,0,0) if name=='top' else norm((-view[1],view[0],0))
        up = cross(view,right)
        projected = [(dot(p,right),dot(p,up)) for _,ps in faces for p in ps]
        lo,hi = min(x for x,y in projected),max(x for x,y in projected)
        bot,top = min(y for x,y in projected),max(y for x,y in projected)
        scale = min(1100/(hi-lo),645/(top-bot))
        img = Image.new('RGB',(1200,850),(232,238,240))
        draw = ImageDraw.Draw(img)
        sortedfaces = sorted(faces,key=lambda e:sum(dot(p,view) for p in e[1])/len(e[1]))
        for material,points in sortedfaces:
            a,b,c = points[:3]
            n = cross(tuple(v-u for u,v in zip(a,b)),tuple(v-u for u,v in zip(a,c)))
            length = math.sqrt(dot(n,n))
            if length<1e-8 or dot(n,view)<=0:
                continue
            light = .65+.35*abs(dot(norm(n),norm((-.3,-.6,1))))
            color = tuple(int(min(255,v*light)) for v in palette[material])
            xy = [(50+(dot(p,right)-lo)*scale,110+(top-dot(p,up))*scale) for p in points]
            draw.polygon(xy,fill=color)
        draw.text((32,24),'Alibaba Xixi A - current sources - CPU '+name+' candidate',font=font,fill=(23,40,49))
        draw.text((32,60),'A1-A8 + 4 mapped links; pleated glass / white fins / woven folded eaves / V trusses.',font=small,fill=(55,69,77))
        draw.text((32,795),'CPU painter preview, not a GLB or game screenshot. Heights estimated +/-4-6 m; A9, historical sixunits, exact entries and full links pending.',font=small,fill=(55,69,77))
        draw.text((32,821),'Painter sorting can produce artificial overlap; it is not a GPU material or silhouette acceptance.',font=small,fill=(55,69,77))
        path = HERE/('cpu-preview-'+name+'.png')
        img.save(path)
        images.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {'sourceModuleSha256':hashlib.sha256((ROOT/'scripts/landmarks/alibaba_a.py').read_bytes()).hexdigest(),
                'specSha256':hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest(),
                'command':'python3 docs/hangzhou/research/ali/alibaba-a-round2/render_cpu_preview.py',
                'kind':'CPU orthographic painter geometry preview, not real game screenshot','images':images}
    (HERE/'cpu-preview-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Saved four CPU previews, including isolated central link, bound to module/spec hashes')


if __name__ == '__main__':
    main()
