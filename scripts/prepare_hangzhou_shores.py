"""Prepare four bounded shore contacts from frozen, source-owned bank lines.

Only the tagged retaining-wall segment receives authored masonry. Other banks
remain land-material skirts; no water plane, footway, or surveyed wall is invented.
"""
from pathlib import Path
import argparse,json,math
import numpy as np
import shapely
from shapely.geometry import Polygon,Point,LineString
from hangzhou_surface import Surface,digest
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--proposal',required=True);ap.add_argument('--city-root',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    package=ROOT/args.proposal;root=ROOT/args.city_root;out=(ROOT/args.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh isolated candidate required')
    provenance=json.loads((package/'package-manifest.json').read_text())
    for dependency in provenance['sourceInputs']+provenance['files']:
        if digest(ROOT/dependency['path'])!=dependency['sha256']:raise ValueError('Changed shore evidence '+dependency['path'])
    proposals=json.loads((package/'proposals.json').read_text())['proposals'];city=json.loads((root/'city.json').read_text());field=Surface(root)
    if city['meta']['cityId']!='hangzhou':raise ValueError('Wrong city')
    reference=json.loads((ROOT/'artifacts/cities/hangzhou/water-data-v3/city.json').read_text())
    if city['water']!=reference['water']:raise ValueError('Water source changed after shoreline evidence')
    wet=shapely.union_all([Polygon(w['rings'][0],w['rings'][1:]) for w in city['water']]);records=[];out.mkdir(parents=True)
    for proposal in proposals:
        points=proposal['geometryGame']['coordinates'];water=proposal['provisionalWaterHeightGame'];bottom=water-.3
        line=LineString(points)
        if line.hausdorff_distance(wet.boundary.intersection(line.buffer(.001)))>.001+1e-9:raise ValueError('Bank no longer matches physical wet boundary')
        sampled=[tuple(points[0])];max_error=0
        for a,b in zip(points,points[1:]):
            stack=[(tuple(a),tuple(b))]
            while stack:
                aa,bb=stack.pop();mid=((aa[0]+bb[0])/2,(aa[1]+bb[1])/2);error=abs(field.ground(*mid)-(field.ground(*aa)+field.ground(*bb))/2)
                if math.dist(aa,bb)>2 or error>.01:
                    if math.dist(aa,bb)<.001:raise ValueError('Unresolved shoreline height discontinuity')
                    stack.extend([(mid,bb),(aa,mid)]);continue
                sampled.append(bb);max_error=max(max_error,error)
        side=None
        for a,b in zip(sampled,sampled[1:]):
            dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);nx,nz=-dz/length,dx/length;x,z=(a[0]+b[0])/2,(a[1]+b[1])/2
            left=wet.covers(Point(x+nx*.3,z+nz*.3));right=wet.covers(Point(x-nx*.3,z-nz*.3))
            if left==right:raise ValueError('Ambiguous wet/dry bank side '+proposal['id'])
            current=-1 if left else 1
            if side is not None and side!=current:raise ValueError('Bank wet side changes')
            side=current
        backs=[];height=[];back_height=[]
        for i,p in enumerate(sampled):
            before=sampled[max(0,i-1)];after=sampled[min(len(sampled)-1,i+1)];dx,dz=after[0]-before[0],after[1]-before[1];length=math.hypot(dx,dz)
            back=(p[0]-dz/length*.12*side,p[1]+dx/length*.12*side)
            if wet.covers(Point(back)):raise ValueError('Dry-side thickness entered water')
            h,hb=field.ground(*p),field.ground(*back)
            if min(h,hb)<water:raise ValueError('Estimated bank ground below estimated water; no clamping permitted')
            backs.append(back);height.append(h);back_height.append(hb)
        footprint=Polygon(sampled+list(reversed(backs)))
        if not footprint.is_valid:raise ValueError('Invalid narrow bank solid')
        faces=[]
        def quad(a,b,c,d):faces.extend([(a,b,c),(a,c,d)])
        # Ring order is corrected globally, rather than guessed per source way.
        front=[(*p,h) for p,h in zip(sampled,height)];back=[(*p,h) for p,h in zip(backs,back_height)]
        low_front=[(*p,bottom) for p in sampled];low_back=[(*p,bottom) for p in backs]
        for i in range(len(sampled)-1):
            j=i+1
            quad(front[i],front[j],back[j],back[i]);quad(low_front[i],low_back[i],low_back[j],low_front[j])
            quad(low_front[i],low_front[j],front[j],front[i]);quad(low_back[j],low_back[i],back[i],back[j])
        quad(low_front[0],front[0],back[0],low_back[0]);quad(low_front[-1],low_back[-1],back[-1],front[-1])
        triangles=np.asarray(faces,dtype='<f8')
        # Top faces should point up. Flip the complete closed shell together.
        if np.cross(triangles[0,1]-triangles[0,0],triangles[0,2]-triangles[0,0])[2]<0:triangles=triangles[:,::-1].copy()
        material='seawall' if proposal.get('sourceTags',{}).get('barrier')=='retaining_wall' else 'land'
        center=line.interpolate(.5,normalized=True);name=f'coastal_shore_{math.floor(center.x/640)}_{math.floor(center.y/640)}'
        filename=proposal['id']+'.npz';np.savez_compressed(out/filename,**{material:triangles})
        records.append({'id':proposal['id'],'name':name,'file':filename,'sha256':digest(out/filename),'material':material,'triangles':len(triangles),'lengthGame':line.length,'sourceId':proposal.get('sourceId'),'riverSourceId':proposal['waterSourceId'],'stations':len(sampled),'heightRangeGame':[min(height+back_height),max(height+back_height)],'bottomYGame':bottom,'waterYGame':water,'thicknessGame':.12,'maxMidpointHeightErrorGame':max_error,'sourceLineSha256':__import__('hashlib').sha256(line.wkb).hexdigest(),'collisionStatus':'ground-to-water side contact only; below local ground, no new above-ground obstacle','basis':'mapped retaining-wall alignment; material/height estimated' if material=='seawall' else 'mapped wet/dry bank terrain contact; no claim of existing masonry'})
    inputs=[package/'package-manifest.json',package/'proposals.json',root/'city.json',root/'geography/manifest.json',root/'geography'/field.manifest['terrainFile'],root/'geography'/field.manifest['roadLevelsFile'],Path(__file__),ROOT/'scripts/hangzhou_surface.py']
    report={'cityId':'hangzhou','kind':'four-source-shore-contact-candidate','objects':records,'inputs':{str(p.relative_to(ROOT)):digest(p) for p in inputs},'units':'game metres; never scale again','pending':['actual GLB float32 topology','final terrain boundary stitching','city balcony and other structure ownership/vertical overlap','shore collision and water access','current browser/day-night/performance']}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(records,indent=2))
if __name__=='__main__':main()
