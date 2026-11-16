import runpy,ast
from pathlib import Path
scope=runpy.run_path(str(Path(__file__).with_name('propose.py')));globals().update({k:v for k,v in scope.items() if not k.startswith('__')})
# Use reviewed independent triangle-intersection implementation, extracting functions only (no prior-folder side effects).
previous=ROOT/'docs/hangzhou/research/coastal-adaptation-round1/export-contract/shore-model-v2-review/intersections.py'
bind(previous.relative_to(ROOT));tree0=ast.parse(previous.read_text());functions=ast.Module(body=[n for n in tree0.body if isinstance(n,ast.FunctionDef) and n.name in ['intri','tri_intersection']],type_ignores=[]);exec(compile(functions,str(previous),'exec'),globals())
actual,g=glb(exp+'coastal-shoreline.glb');bal,bg=glb(base+'landmarks/city-balcony-v1/city-balcony.glb')
allrows=[]
for candidate in candidates:
 by=candidate['baseYGame'];rows=[]
 for shorepart in actual:
  sts=shorepart['triangles'];polys=[Polygon(t[:,:2]) for t in sts];tree=STRtree(polys);parts=[]
  for part in bal:
   pairs=[]
   shifted=part['triangles']+np.array([0,0,by])
   for i,t in enumerate(shifted):
    for j in map(int,tree.query(Polygon(t[:,:2]))):
     st0=sts[j]
     if t[:,2].min()>st0[:,2].max()+1e-6 or t[:,2].max()<st0[:,2].min()-1e-6:continue
     hit=tri_intersection(t,st0)
     if hit:pairs.append({'balconyTriangle':i,'shoreTriangle':j,'balconyYRange':[float(t[:,2].min()),float(t[:,2].max())],**hit})
   parts.append({'name':part['name'],'pairs':pairs,'pairCount':len(pairs),'uniqueBalconyFaces':len(set(p['balconyTriangle'] for p in pairs))})
  rows.append({'shore':shorepart['name'],'parts':parts,'totalPairCount':sum(p['pairCount'] for p in parts)})
  print(candidate['id'],shorepart['name'],rows[-1]['totalPairCount'],flush=True)
 allrows.append({'datumCandidate':candidate['id'],'baseYGame':by,'upperYGame':candidate['upperYGame'],'rigidShiftOnly':True,'fingerProfileNotBuilt':True,'shores':rows})
save('datum-vs-four-shores-3d.json',allrows);save('input-bindings.json',bindings)
