"""Offline orthographic geometry illustration. This does not start the game or verify GPU appearance."""
import hashlib,json,math,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
source=Path(sys.argv[2]) if len(sys.argv)>2 else Path('artifacts/cities/hangzhou/bus-depot-profile-v2/contact-v4/generated-bus-mesh-v4.json')
output=Path(sys.argv[1]);assert not output.exists();assert source.stat().st_size<3*1024*1024
raw=source.read_bytes();model=json.loads(raw)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def unit(a):
 n=math.sqrt(dot(a,a));return [v/n for v in a]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
view=unit([8,4.2,11]);right=unit(cross([0,1,0],view));up=cross(view,right);light=unit([-.3,1,.8])
def project(p):return [dot(p,right),-dot(p,up)]
vertices=[p['positions'][i:i+3] for p in model['parts'] for i in range(0,len(p['positions']),3)]
points=[project(p) for p in vertices];lo=[min(p[k] for p in points) for k in range(2)];hi=[max(p[k] for p in points) for k in range(2)]
scale=min(1020/(hi[0]-lo[0]),400/(hi[1]-lo[1]));offset=[600-(lo[0]+hi[0])*scale/2,350-(lo[1]+hi[1])*scale/2]
def xy(p):return tuple(round(v*scale+offset[k],2) for k,v in enumerate(project(p)))
triangles=[]
for part in model['parts']:
 for i in range(0,len(part['indices']),3):
  ids=part['indices'][i:i+3];pts=[part['positions'][j*3:j*3+3] for j in ids];normal=part['normals'][ids[0]*3:ids[0]*3+3]
  if dot(normal,view)<=1e-6:continue
  color=part['colors'][ids[0]*4:ids[0]*4+3];shade=.70+.30*max(0,dot(normal,light));rgba=tuple(max(0,min(255,round(c*shade*255))) for c in color)+(120 if part['materialClass']=='glass' else 255,)
  depths=[dot(p,view) for p in pts]
  triangles.append((sum(depths)/3,[xy(p) for p in pts],rgba,depths))
image=Image.new('RGB',(1200,650),'#eaf0ed');draw=ImageDraw.Draw(image,'RGBA')
draw.rounded_rectangle((24,18,1176,625),radius=24,fill=(249,250,245,255));draw.ellipse((260,484,942,550),fill=(28,55,48,23))
rgb=np.array(image);depth=np.full((650,1200),-np.inf,dtype=np.float32)
def raster(triangle,transparent=False):
 _,pts,color,z=triangle
 left=max(0,math.floor(min(p[0] for p in pts)));right_edge=min(1199,math.ceil(max(p[0] for p in pts)))
 top=max(0,math.floor(min(p[1] for p in pts)));bottom=min(649,math.ceil(max(p[1] for p in pts)))
 if right_edge<left or bottom<top:return
 (ax,ay),(bx,by),(cx,cy)=pts;den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
 if abs(den)<1e-8:return
 yy,xx=np.mgrid[top:bottom+1,left:right_edge+1];xx=xx+.5;yy=yy+.5
 a=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den;b=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;c=1-a-b
 values=a*z[0]+b*z[1]+c*z[2];target_depth=depth[top:bottom+1,left:right_edge+1]
 valid=(a>=-1e-8)&(b>=-1e-8)&(c>=-1e-8)&(values>target_depth)
 target=rgb[top:bottom+1,left:right_edge+1]
 if transparent:
  alpha=color[3]/255;target[valid]=(np.asarray(color[:3])*alpha+target[valid]*(1-alpha)).astype(np.uint8)
 else:target[valid]=color[:3];target_depth[valid]=values[valid]
for t in triangles:
 if t[2][3]==255:raster(t)
for t in sorted(triangles,key=lambda t:t[0]):
 if t[2][3]<255:raster(t,True)
image=Image.fromarray(rgb);draw=ImageDraw.Draw(image,'RGBA')
font='/System/Library/Fonts/Hiragino Sans GB.ttc'
draw.text((58,40),'杭城之行 · 公交模型候选',font=ImageFont.truetype(font,28),fill='#183a34')
draw.text((58,82),'离线几何投影 · 不是游戏实机截图',font=ImageFont.truetype(font,18),fill='#59716a')
draw.text((58,571),'车体、轮胎接触与车门共用规格；整车外观和乘车视角仍待实机验收。',font=ImageFont.truetype(font,17),fill='#59716a')
output.parent.mkdir(parents=True,exist_ok=True);image.save(output)
report={'schemaVersion':1,'kind':'offline geometry illustration only','renderer':'CPU depth-buffer opaque surfaces; illustrative diffuse lighting and transparent glass','source':str(source),'sourceSha256':hashlib.sha256(raw).hexdigest(),'image':str(output),'imageSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'sourceTriangles':model['triangleCount'],'drawnFrontTriangles':len(triangles),'projection':{'view':view,'orthographic':True},'gameEngineStarted':False,'browserAccepted':False,'texturesOrSignLetteringRendered':False}
output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
