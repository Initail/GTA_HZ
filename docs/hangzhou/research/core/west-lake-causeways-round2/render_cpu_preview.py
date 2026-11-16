"""Small CPU painter previews. Never described as GLB or game screenshots."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def dot(p,q):return sum(a*b for a,b in zip(p,q))
def norm(p):
    l=math.sqrt(dot(p,p));return tuple(v/l for v in p)
def cross(p,q):return p[1]*q[2]-p[2]*q[1],p[2]*q[0]-p[0]*q[2],p[0]*q[1]-p[1]*q[0]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    spec=json.loads((HERE/'spec.json').read_text());checker=load('causeways_checker',HERE/'check_candidate.py')
    mod=load('causeways_cpu',ROOT/'scripts/landmarks/west_lake_causeways.py');c=checker.Collector()
    report=mod.build(c,{'x':0,'z':0,'y':0},spec,.6)
    groups={};face=0
    for part,triangles in report['partTriangles'].items():
        groups[part]=[];n=0
        while n<triangles:
            material,ps=c.faces[face];groups[part].append((material,ps));n+=len(ps)-2;face+=1
    palette={'asphalt':(89,92,90),'concrete':(172,168,151),'park':(104,135,63),'pavement':(188,186,170),'roof':(88,90,82)}
    titlefont=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',25)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
    images=[]
    for name,direction,selected in [('map-top',(0,0,1),None),('distant-southeast',(1,-1,.7),None),
        ('jindai-side',(1,-.83,.04),'bridge-28538285'),('wangshan-side',(1,.28,.05),'bridge-30072139')]:
        faces=c.faces if selected is None else groups[selected]
        view=norm(direction);right=(1,0,0) if name=='map-top' else norm((-view[1],view[0],0));up=cross(view,right)
        qs=[(dot(p,right),dot(p,up)) for _,ps in faces for p in ps]
        left,bot=min(p[0] for p in qs),min(p[1] for p in qs);r,top=max(p[0] for p in qs),max(p[1] for p in qs)
        size=(1200,1250) if name=='map-top' else (1200,760)
        scale=min(1090/(r-left),(size[1]-210)/(top-bot))
        if selected:scale=min(scale,145)
        img=Image.new('RGB',size,(222,234,239));d=ImageDraw.Draw(img)
        xpad=(size[0]-(r-left)*scale)/2;ypad=110+(size[1]-210-(top-bot)*scale)/2
        light=norm((-.3,-.6,1))
        for mat,ps in sorted(faces,key=lambda f:sum(dot(p,view) for p in f[1])/len(f[1])):
            a,b,c0=ps[:3];n=cross(tuple(v-u for u,v in zip(a,b)),tuple(v-u for u,v in zip(a,c0)))
            if dot(n,n)<1e-12 or dot(n,view)<=0:continue
            shade=.60+.40*abs(dot(norm(n),light));color=tuple(int(v*shade) for v in palette[mat])
            p=[(xpad+(dot(q,right)-left)*scale,ypad+(top-dot(q,up))*scale) for q in ps];d.polygon(p,fill=color)
        d.text((30,24),'West Lake Bai / Su Causeways - CPU '+name,font=titlefont,fill=(20,39,43))
        d.text((30,61),'19 fixed source paths / 7 distinct stone arches / mapped bank strips. Broken Bridge externally owned.',font=font,fill=(40,60,64))
        d.text((30,size[1]-76),'No lake mesh in candidate. Tree inventory / lamps / current water datum / runtime walk heights pending.',font=font,fill=(40,60,64))
        d.text((30,size[1]-47),'CPU painter only; no game screenshot, GPU material, collision or performance acceptance.',font=font,fill=(40,60,64))
        if name=='map-top':
            d.text((1100,105),'N',font=titlefont,fill=(20,39,43));d.line([(1122,173),(1122,136)],fill=(20,39,43),width=3)
            d.polygon([(1122,132),(1117,144),(1127,144)],fill=(20,39,43))
        p=HERE/('cpu-preview-'+name+'.png');img.save(p);images.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'kind':'CPU geometry preview','actualInGameScreenshot':False})
    result={'sourceModuleSha256':sha(ROOT/'scripts/landmarks/west_lake_causeways.py'),'specSha256':sha(HERE/'spec.json'),
        'command':'bundled python3 -B docs/hangzhou/research/core/west-lake-causeways-round2/render_cpu_preview.py',
        'images':images,'limits':'painter sorting/material palette are approximate; no base city, water or canopy meshes are loaded'}
    (HERE/'cpu-preview-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Saved four source/module-bound CPU previews; no actual game screenshots')

if __name__=='__main__':main()
