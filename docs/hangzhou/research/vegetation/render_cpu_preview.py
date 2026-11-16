"""CPU contact sheets at one common game-unit scale; no scene/browser render."""
import hashlib,importlib.util,json,math,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def dot(p,q):return sum(a*b for a,b in zip(p,q))
def cross(p,q):return p[1]*q[2]-p[2]*q[1],p[2]*q[0]-p[0]*q[2],p[0]*q[1]-p[1]*q[0]
def norm(p):
    n=math.sqrt(dot(p,p));return tuple(v/n for v in p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    mod=load('hz_tree_palette',ROOT/'scripts/landmarks/hangzhou_tree_palette.py');check=load('tree_checker',HERE/'check_palette.py')
    palette=json.loads((HERE/'palette-spec.json').read_text());defs=mod.material_definitions();mapping={k:v['name'] for k,v in defs.items()}
    colors={v['name']:tuple(int(x*255) for x in v['color']) for v in defs.values()}
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
    images=[]
    for name,angle in [('front',0),('diagonal',math.pi/4)]:
        im=Image.new('RGB',(2240,1260),(230,237,239));d=ImageDraw.Draw(im)
        view=norm((math.sin(angle),-math.cos(angle),.12));right=norm((-view[1],view[0],0));up=cross(view,right)
        d.text((25,18),'Hangzhou original tree archetypes - CPU '+name+' - full / mid / far LOD',font=font,fill=(24,41,43))
        d.text((25,54),'All cells use22 pixels per game metre. Dimensions are estimated real metres x0.60 once. Source photos are not textures.',font=small,fill=(46,60,62))
        for col,sp in enumerate(palette['species']):
            for lod in range(3):
                spec=json.loads((HERE/f'prototype-specs/{sp["id"]}-lod{lod}.json').read_text());spec['materialMap']=mapping;c=check.Collector();report=mod.build(c,{'x':0,'z':0,'y':0},spec,.6)
                ox=col*280+140;base=445+lod*350
                d.line([(col*280+20,base),(col*280+260,base)],fill=(150,164,158),width=1)
                for mat,ps in sorted(c.faces,key=lambda f:sum(dot(p,view) for p in f[1])/len(f[1])):
                    a,b,e=ps[:3];n=cross(tuple(v-u for u,v in zip(a,b)),tuple(v-u for u,v in zip(a,e)))
                    if dot(n,n)<1e-12 or dot(n,view)<=0:continue
                    light=.69+.31*max(0,dot(norm(n),norm((-.3,-.5,1))));color=tuple(int(v*light) for v in colors[mat])
                    p=[(ox+dot(q,right)*22,base-dot(q,up)*22) for q in ps];d.polygon(p,fill=color)
                d.text((col*280+20,base+15),sp['id']+' / LOD'+str(lod),font=font,fill=(24,41,43))
                d.text((col*280+20,base+45),str(report['triangles'])+' tris; h'+str(sp['prototypeHeightM'])+'m / r'+str(sp['prototypeCrownRadiusM'])+'m',font=small,fill=(46,60,62))
        d.text((25,1215),'CPU painter only; no actual GLB/GPU/game screenshots, no canopy placement, clearance or performance pass.',font=small,fill=(46,60,62))
        p=HERE/('cpu-palette-'+name+'.png');im.save(p);images.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'actualInGameScreenshot':False})
    # Close plant-specific silhouette detail, and staticseason variants. The
    # registered authoredpalette is simulated only inthisCPU painter.
    im=Image.new('RGB',(1500,650),(230,237,239));d=ImageDraw.Draw(im)
    d.text((24,18),'Static authored season/detail variants - CPU only; no seasonal gameplay claimed',font=font,fill=(24,41,43))
    cases=[('willow','summer'),('ginkgo','autumn'),('peach','spring'),('osmanthus','autumn'),('plane','winter')]
    view=norm((0,-1,.10));right=(1,0,0);up=cross(view,right)
    for col,(sid,season) in enumerate(cases):
        spec=json.loads((HERE/f'prototype-specs/{sid}-lod0.json').read_text());spec['season']=season;spec['materialMap']=mapping;c=check.Collector();report=mod.build(c,{'x':0,'z':0,'y':0},spec,.6)
        ps=[p for _,face in c.faces for p in face];maxh=max(p[2] for p in ps);extent=max(abs(p[0]) for p in ps);zoom=min(220/(extent*2),440/maxh);ox=150+col*300;base=535
        for mat,ps in sorted(c.faces,key=lambda f:sum(dot(p,view) for p in f[1])/len(f[1])):
            a,b,e=ps[:3];n=cross(tuple(v-u for u,v in zip(a,b)),tuple(v-u for u,v in zip(a,e)))
            if dot(n,n)<1e-12 or dot(n,view)<=0:continue
            color=tuple(int(v*(.69+.31*max(0,dot(norm(n),norm((-.3,-.5,1)))))) for v in colors[mat]);d.polygon([(ox+dot(q,right)*zoom,base-dot(q,up)*zoom) for q in ps],fill=color)
        d.text((col*300+25,554),sid+' / '+season,font=font,fill=(24,41,43))
    d.text((25,607),'Different zoom per cell. Allsizes/branchshapes remainestimated archetypes. Currentphenology/pruning/cultivars unverified.',font=small,fill=(46,60,62))
    p=HERE/'cpu-static-season-details.png';im.save(p);images.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'actualInGameScreenshot':False})
    (HERE/'cpu-preview-manifest.json').write_text(json.dumps({'sourceModuleSha256':sha(ROOT/'scripts/landmarks/hangzhou_tree_palette.py'),'paletteSpecSha256':sha(HERE/'palette-spec.json'),'images':images,'kind':'CPU painter only; materialregistration not yet exported/GPUtested'},ensure_ascii=False,indent=2)+'\n')
    print('Saved three CPU tree/LOD/season sheets, bound to currentmodule andspec')

if __name__=='__main__':main()
