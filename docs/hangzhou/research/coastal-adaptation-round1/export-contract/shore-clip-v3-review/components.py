from pathlib import Path
source=Path(__file__).with_name('check.py').read_text().split('ap=argparse.ArgumentParser')[0];exec(compile(source,str(Path(__file__).with_name('check.py')),'exec'),globals())
parts,_=glb('artifacts/cities/hangzhou/shore-glb-v3/coastal-shoreline.glb');rows=[]
for p in parts:
 ts=p['triangles'];verts,inds=np.unique(ts.reshape(-1,3),axis=0,return_inverse=True);ids=inds.reshape(-1,3);parents=list(range(len(verts)))
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for a,b,c in ids:parents[root(int(a))]=root(int(b));parents[root(int(b))]=root(int(c))
 groups={}
 for i,t in enumerate(ids):groups.setdefault(root(int(t[0])),[]).append(i)
 rows.append({'name':p['name'],'components':[topology(ts[index]) for index in groups.values()]})
save('connected-components.json',rows)
