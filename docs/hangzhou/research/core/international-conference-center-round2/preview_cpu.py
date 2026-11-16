"""Draft orthographic CPU views, explicitly not current game screenshots."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw
from validate_cpu import BRecorder,load,sub,cross,dot

OUT=Path(__file__).resolve().parent
COLORS={'gold':(195,148,64),'steel':(85,106,111),'darkglass':(47,66,68),'landmarkglass':(74,112,133)}


def main():
    spec,path,mod=load();rec=BRecorder();mod.build(rec,{'x':0,'z':0,'y':0},spec,.6)
    triangles=[(mat,[ps[0],ps[i],ps[i+1]]) for mat,ps in rec.faces for i in range(1,len(ps)-1)]
    front=math.degrees(spec['axisRadiansEastCCW']+spec['glazedFaceRelativeRadians'])
    result=[]
    for title,az,el,name in [('TOP / north roughly up',-90,89.95,'cpu-top.png'),
        ('STREET / theatre-facing NE side',front,4,'cpu-street.png'),
        ('DISTANT / theatre-facing oblique',front+20,27,'cpu-distant.png')]:
        az,el=math.radians(az),math.radians(el)
        eye=(math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el))
        right=(-math.sin(az),math.cos(az),0)
        up=(-math.cos(az)*math.sin(el),-math.sin(az)*math.sin(el),math.cos(el))
        projected=[]
        for mat,pts in triangles:
            normal=cross(sub(pts[1],pts[0]),sub(pts[2],pts[0]));norm=math.sqrt(dot(normal,normal))
            if dot(normal,eye)<=0:continue
            shade=.45+.55*max(0,dot(normal,(.36,-.48,.80))/norm)
            color=tuple(round(c*shade) for c in COLORS[mat])
            q=[(dot(p,right),dot(p,up)) for p in pts]
            projected.append((sum(dot(p,eye) for p in pts)/3,color,q))
        xs=[p[0] for d,c,q in projected for p in q];ys=[p[1] for d,c,q in projected for p in q]
        lo,hi=min(xs),max(xs);bot,top=min(ys),max(ys)
        factor=min(1320/(hi-lo),680/(top-bot));cx=(lo+hi)/2;cy=(bot+top)/2
        im=Image.new('RGB',(1440,850),(236,239,237));draw=ImageDraw.Draw(im)
        for depth,color,q in sorted(projected,key=lambda x:x[0]):
            draw.polygon([(720+(x-cx)*factor,435-(y-cy)*factor) for x,y in q],fill=color)
        draw.text((24,22),'HANGZHOU ICC | CPU B GEOMETRY PREVIEW | '+title,fill=(30,40,45))
        draw.text((24,795),'SECTION ESTIMATED / NO BLENDER OR BABYLON / NO SITE GROUND / GLASS COLORS PROVISIONAL',fill=(40,50,54))
        draw.text((24,817),'Not a real game screenshot, current condition survey, collision or visual acceptance.',fill=(40,50,54))
        p=OUT/name;im.save(p)
        result.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,
          'cameraAzimuthEastCCW':math.degrees(az),'cameraElevation':math.degrees(el),
          'scope':'CPU orthographic draft; no renderer or material validation'})
    report={'schemaVersion':1,'sourceModuleSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
      'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
      'previewMethod':'Pillow painter of front-facing CPU triangle fans; no Blender/browser/render-engine invocation',
      'previews':result,'imagesAreGameScreenshots':False,'visualAcceptance':'pending GLB/day/night/context review'}
    (OUT/'cpu-preview-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'cpuPreviews':len(result),'gameScreenshots':0},ensure_ascii=False))


if __name__=='__main__':main()
