"""Rasterize actual Hangzhou floor/world-top ordinates for the original AO bake.

Ground is the same source-road earthworks function, evaluated in vector batches.
4-game-metre cells are a lighting approximation, not improved DSM resolution.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from affine import Affine
from hangzhou_surface import Surface,digest
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--city-root',required=True);p.add_argument('--floors',required=True);p.add_argument('--lookup',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    root=ROOT/a.city_root;out=(ROOT/a.output).resolve()
    if ROOT/'artifacts' not in out.parents or out.exists():raise ValueError('Fresh artifact output required')
    began=time.monotonic();city=json.loads((root/'city.json').read_text());field=Surface(root)
    lookup=json.loads((ROOT/a.lookup).read_text())['lookup'];width,height,cell,x0,z0=[lookup[k] for k in ['width','height','cell','minX','minZ']]
    if city['meta']['cityId']!='hangzhou' or cell!=4:raise ValueError('Wrong city/lighting cell')
    x=x0+(np.arange(width,dtype=np.float64)+.5)*cell;z=z0+(np.arange(height,dtype=np.float64)+.5)*cell
    total=np.zeros((height,width),dtype=np.float64);weighted=np.zeros_like(total);influence=np.zeros_like(total)
    ground=np.zeros_like(total);g=field.grid
    # Same SW/NE triangle choice as Surface.terrain; outside the source is zero.
    for start in range(0,height,64):
        zz=z[start:start+64,None];u=np.broadcast_to((x[None,:]-g['x0'])/g['step'],(len(zz),width));v=np.broadcast_to((zz-g['z0'])/g['step'],u.shape)
        ii=np.floor(u).astype(int);jj=np.floor(v).astype(int);valid=(ii>=0)&(jj>=0)&(ii<g['columns']-1)&(jj<g['rows']-1)
        i=np.clip(ii,0,g['columns']-2);j=np.clip(jj,0,g['rows']-2);fx=u-ii;fz=v-jj
        aa=field.values[j,i].astype(float);bb=field.values[j,i+1].astype(float);dd=field.values[j+1,i].astype(float);cc=field.values[j+1,i+1].astype(float)
        ground[start:start+64]=np.where(valid,np.where(fx+fz<=1,aa+(bb-aa)*fx+(dd-aa)*fz,cc+(dd-cc)*(1-fx)+(bb-cc)*(1-fz)),0)
    segments=0
    for road in field.levels['roads']:
        if road['tier']!=0:continue
        margin=road['width']/2+field.transition
        for n,(aa,bb) in enumerate(zip(road['points'],road['points'][1:])):
            c0=max(0,math.ceil((min(aa[0],bb[0])-margin-x0)/cell-.5));c1=min(width,math.floor((max(aa[0],bb[0])+margin-x0)/cell-.5)+1)
            r0=max(0,math.ceil((min(aa[1],bb[1])-margin-z0)/cell-.5));r1=min(height,math.floor((max(aa[1],bb[1])+margin-z0)/cell-.5)+1)
            if c1<=c0 or r1<=r0:continue
            dx,dz=bb[0]-aa[0],bb[1]-aa[1];xx=x[None,c0:c1]-aa[0];zz=z[r0:r1,None]-aa[1]
            t=np.clip((xx*dx+zz*dz)/(dx*dx+dz*dz or 1),0,1);distance=np.hypot(xx-dx*t,zz-dz*t)
            edge=np.clip((distance-road['width']/2)/field.transition,0,1);w=1-edge*edge*(3-2*edge);ys=road['heights'][n]+(road['heights'][n+1]-road['heights'][n])*t
            total[r0:r1,c0:c1]+=w;weighted[r0:r1,c0:c1]+=ys*w;np.maximum(influence[r0:r1,c0:c1],w,out=influence[r0:r1,c0:c1]);segments+=1
    active=total>0;ground[active]+=(weighted[active]/total[active]-ground[active])*influence[active]
    del total,weighted,influence
    # Independently query the scalar runtime-parity sampler at fixed random cells.
    rng=np.random.default_rng(73603);errors=[]
    for row,col in zip(rng.integers(0,height,4096),rng.integers(0,width,4096)):errors.append(abs(ground[row,col]-field.ground(float(x[col]),float(z[row]))))
    if max(errors)>1e-7:raise ValueError('Vector/scalar ground mismatch '+str(max(errors)))
    minimum=float(ground.min());span=max(1e-6,float(ground.max())-minimum);alpha=np.rint((ground-minimum)/span*255).astype('u1');decoded=minimum+alpha.astype(float)/255*span
    quantization_error=float(np.max(np.abs(decoded-ground)));del ground
    floors=json.loads((ROOT/a.floors).read_text());floor_by_id={}
    for f in floors:floor_by_id.setdefault(f['id'],[]).append(f)
    objects=[]
    for index,b in enumerate(city['buildings']):
        top=b.get('maxY',b['height']);matches=[f for f in floor_by_id.get(b.get('id'),[]) if abs(f['mainRoofYGame']-top)<1e-7]
        if matches:top=max(f['visualMaximumYGame'] for f in matches)
        objects.append(({'type':'Polygon','coordinates':b['rings']},top,index+1))
    objects.sort(key=lambda item:item[1]);shape=(height,width);transform=Affine(cell,0,x0,0,cell,z0)
    tops=rasterize([(geo,value) for geo,value,_ in objects],out_shape=shape,transform=transform,dtype='float32',fill=0)
    ids=rasterize([(geo,index) for geo,_,index in objects],out_shape=shape,transform=transform,dtype='int32',fill=0)
    out.mkdir(parents=True);tops.astype('<f4').tofile(out/'heights.f32');ids.astype('<i4').tofile(out/'ids.i32');decoded.astype('<f4').tofile(out/'ground.f32');alpha.tofile(out/'ground.u8')
    inputs={str(p.relative_to(ROOT)):digest(p) for p in [root/'city.json',root/'geography/manifest.json',root/'geography'/field.manifest['terrainFile'],root/'geography'/field.manifest['roadLevelsFile'],ROOT/a.floors,ROOT/a.lookup,Path(__file__),ROOT/'scripts/hangzhou_surface.py']}
    report={'cityId':'hangzhou','grid':{k:lookup[k] for k in ['width','height','cell','minX','minZ']},'groundRange':[minimum,span],'heightReference':'terrain','sourceBuildings':len(objects),'groundSegments':segments,'groundScalarParity':{'samples':len(errors),'maxErrorGame':max(errors),'pass':True},'groundAlphaQuantizationErrorGame':quantization_error,'inputs':inputs,'files':{p.name:digest(p) for p in out.iterdir()},'seconds':time.monotonic()-began,'status':'lighting-only inputs, no physical/visual acceptance','pending':['horizon bake','runtime terrain-relative material sampling','visual/performance inspection']}
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
