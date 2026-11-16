"""Original orthographic B-face drafts; not Blender/game/visual acceptance."""
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
from PIL import Image,ImageDraw
from validate_cpu import fixture

OUT=Path(__file__).resolve().parent
COLORS={'gold':(192,145,63),'concrete':(195,193,183),'civicred':(127,35,31),
        'roof':(58,64,65),'darkglass':(35,35,34),'landmarkglass':(74,130,104)}


def render(b,name,azimuth,elevation,selection=None):
    faces=b.faces if selection is None else b.faces[selection[0]:selection[1]]
    points=[p for _,face in faces for p in face]
    center=[(min(p[i] for p in points)+max(p[i] for p in points))/2 for i in range(3)]
    a,e=math.radians(azimuth),math.radians(elevation)
    ca,sa,ce,se=math.cos(a),math.sin(a),math.cos(e),math.sin(e)
    def projection(p):
        x,z,h=[p[i]-center[i] for i in range(3)]
        u=-x*sa+z*ca
        v=-se*(x*ca+z*sa)+ce*h
        depth=ce*(x*ca+z*sa)+se*h
        return u,v,depth
    mapped=[(mat,[projection(p) for p in face]) for mat,face in faces]
    allp=[p for _,f in mapped for p in f]
    lo=[min(p[i] for p in allp) for i in [0,1]]
    hi=[max(p[i] for p in allp) for i in [0,1]]
    width,height=1100,850
    scale=min((width-70)/(hi[0]-lo[0]),(height-110)/(hi[1]-lo[1]))
    def screen(p):return (width/2+(p[0]-(lo[0]+hi[0])/2)*scale,height/2-(p[1]-(lo[1]+hi[1])/2)*scale+25)
    image=Image.new('RGB',(width,height),(227,236,239))
    draw=ImageDraw.Draw(image)
    for mat,face in sorted(mapped,key=lambda item:sum(p[2] for p in item[1])/len(item[1])):
        color=COLORS[mat]
        draw.polygon([screen(p) for p in face],fill=color)
    draw.text((22,18),'CPU ORTHOGRAPHIC DRAFT - synthetic independent hall heights - not a game screenshot',fill=(25,37,44))
    draw.text((22,36),f'{name} | source-bound shells + estimated local terraces/details | all site/entry acceptance pending',fill=(25,37,44))
    image.save(OUT/name)
    return {'path':name,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest(),
      'viewAzimuthEastCCW':azimuth,'viewElevation':elevation,'reviewStatus':'generated; actual view follows',
      'projection':'orthographic CPU painter; approximate alias colors, no Babylon lighting',
      'heightBasis':'deliberately synthetic API fixture; not surveyed site profile'}


def main():
    spec,site,city,s,lm,b,report=fixture()
    views=[render(b,'cpu-top.png',-71.5,88),render(b,'cpu-street.png',-71.5,23),
           render(b,'cpu-distant.png',35,28)]
    start=report['halls'][0]['faces']
    views.append(render(b,'cpu-grand-plaque-close.png',-71.5,4,(start,start+report['halls'][1]['faces'])))
    result={'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'views':views,'sourceModuleSha256':hashlib.sha256((OUT.parents[4]/'scripts/landmarks/lingyin_site.py').read_bytes()).hexdigest(),
      'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
      'limitations':['Not actual screenshots, photographic verification, GLB or material acceptance.',
                     'Synthetic heights demonstrate API, not the current terrain/floor.',
                     'Current global collision/path/day/night/performance are pending.']}
    (OUT/'cpu-preview-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'generatedViews':len(views)},ensure_ascii=False))


if __name__=='__main__':main()
