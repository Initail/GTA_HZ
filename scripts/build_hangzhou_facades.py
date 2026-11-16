"""Candidate adaptation of the upstream facade relief and shared materials.

Uses prepared real polygon holes, game-unit floors and tiled geometry. Replaces
the candidate buildings layer and adds near facades; never writes public.
"""
from __future__ import annotations
import argparse,json,hashlib,math,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--limit-buildings',type=int,default=0);a=ap.parse_args(argv)
    source,output=[(ROOT/p).resolve() for p in [a.input,a.output]];manifest=json.loads((source/'manifest.json').read_text());bp=source/manifest['buildingsFile']
    if ROOT/'artifacts' not in output.parents or output.exists():raise ValueError('Fresh candidate output required')
    if manifest['cityId']!='hangzhou' or sha(bp)!=manifest['buildingsSha256']:raise ValueError('Changed Hangzhou building preparation')
    buildings=json.loads(bp.read_text());source_count=len(buildings);began=time.monotonic()
    if a.limit_buildings<0:raise ValueError('Negative limit')
    if a.limit_buildings:buildings=buildings[::max(1,len(buildings)//a.limit_buildings)][:a.limit_buildings]
    def tile(row):
        r=row['rings'][0];return math.floor(sum(p[0] for p in r)/len(r)/640),math.floor(sum(p[1] for p in r)/len(r)/640)
    buildings.sort(key=tile)
    import city_mesh as cm
    class FacadeMesh(cm.B):
        def __init__(self):super().__init__();self.tint=(1,1,1,1);self.colors=cm.defaultdict(list)
        def face(self,m,pts,uv=None):super().face(m,pts,uv);self.colors[m].extend([self.tint]*len(pts))
        def finish(self,name,smooth=False):
            obs=super().finish(name,False)
            for ob in obs:
                token=ob.data.materials[0].name;attr=ob.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
                if len(attr.data)!=len(self.colors[token]):raise ValueError('Color/mesh loop mismatch')
                for value,color in zip(attr.data,self.colors[token]):value.color=color
            return obs
    for material in cm.M.values():
        p=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED');old=p.inputs['Base Color'];links=list(old.links);socket=links[0].from_socket if links else None
        mix=material.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
        if socket:material.node_tree.links.new(socket,mix.inputs[1])
        else:mix.inputs[1].default_value=old.default_value
        color=material.node_tree.nodes.new('ShaderNodeVertexColor');color.layer_name='Color';material.node_tree.links.new(color.outputs['Color'],mix.inputs[2]);material.node_tree.links.new(mix.outputs[0],old)
    palettes={'office':[(.69,.84,1,1),(.55,.78,.79,1),(.91,.91,.86,1),(.83,.71,.63,1)],'residential':[(.97,.90,.74,1),(.77,.83,.83,1),(.94,.80,.72,1),(.88,.92,.92,1)],'stone':[(1,.9,.78,1),(.84,.88,.95,1),(.93,.76,.67,1)]}
    chunks={};details={};floors=[];balconies=0;holes=0;objects={'buildings':[],'facades':[]};previous=None
    def flush():
        for name,groups,prefix in [('buildings',chunks,'block'),('facades',details,'facade')]:
            for key,b in groups.items():objects[name].extend(b.finish(f'{prefix}_{key[0]}_{key[1]}'))
            groups.clear()
    for index,row in enumerate(buildings):
        typ=row['style'];h=row['height'];base=row['baseYGame'];roof=row['maxY'];rings=row['rings'];key=(math.floor(sum(p[0] for p in rings[0])/len(rings[0])/640),math.floor(sum(p[1] for p in rings[0])/len(rings[0])/640))
        if previous is not None and key!=previous:flush()
        previous=key
        if abs(roof-base-h)>1e-7 or typ not in palettes:raise ValueError('Invalid building floor/style')
        b=chunks.setdefault(key,FacadeMesh());d=details.setdefault(key,FacadeMesh());rnd=random.Random(row['seed']);tint=rnd.choice(palettes[typ]);b.tint=d.tint=tint;shop=min(3.5,h*.25);parapet=max(1.2,h*.035);maximum=roof+parapet;holes+=len(rings)-1
        for number,(ring,bottoms) in enumerate(zip(rings,row['wallBottomHeights'])):
            pairs=list(zip(ring,bottoms));pairs=pairs[:-1] if ring[0]==ring[-1] else pairs
            signed=sum(p[0][0]*q[0][1]-q[0][0]*p[0][1] for p,q in zip(pairs,pairs[1:]+pairs[:1]))
            if (number==0 and signed<0) or (number>0 and signed>0):pairs.reverse()
            for (p,y),(q,yy) in zip(pairs,pairs[1:]+pairs[:1]):
                x,z=p;xx,zz=q;length=math.dist(p,q)
                if length<1e-8:continue
                # Original storefront/upper-wall split, now on its actual floor.
                if y<base-1e-7 or yy<base-1e-7:b.face('concrete',[(x,z,y),(xx,zz,yy),(xx,zz,base),(x,z,base)])
                b.face('darkglass',[(x,z,base),(xx,zz,base),(xx,zz,base+shop),(x,z,base+shop)],[(0,0),(length/24,0),(length/24,shop/24),(0,shop/24)])
                b.face(typ,[(x,z,base+shop),(xx,zz,base+shop),(xx,zz,roof),(x,z,roof)],[(0,shop/24),(length/24,shop/24),(length/24,h/24),(0,h/24)])
                tx,tz=(xx-x)/length,(zz-z)/length;nx,nz=tz,-tx
                def pt(u,dep,height):return x+tx*u+nx*dep,z+tz*u+nz*dep,base+height
                # Solid parapet strip keeps courtyards open; never cap a hole.
                for mat,lo,hi in [('concrete' if typ=='residential' else 'steel',h,h+.4),(typ,h+.4,h+parapet)]:
                    b.face(mat,[pt(0,0,lo),pt(length,0,lo),pt(length,0,hi),pt(0,0,hi)])
                    b.face(mat,[pt(length,-.16,lo),pt(0,-.16,lo),pt(0,-.16,hi),pt(length,-.16,hi)])
                    b.face('roof',[pt(0,0,hi),pt(length,0,hi),pt(length,-.16,hi),pt(0,-.16,hi)])
                if typ=='residential' and h<65:
                    for level in range(6,int(h),4):
                        b.face('concrete',[pt(0,.015,level),pt(length,.015,level),pt(length,.015,level+.16),pt(0,.015,level+.16)])
                if length<7:continue
                if length<50 and h>8:
                    d.tint=(.8,.84,.86,1);u0,u1=.6,length-.6
                    d.face('steel',[pt(u0,.05,3.2),pt(u1,.05,3.2),pt(u1,.85,3.2),pt(u0,.85,3.2)])
                    d.face('silver',[pt(u0,.85,3.15),pt(u1,.85,3.15),pt(u1,.85,3.25),pt(u0,.85,3.25)])
                    for u in range(2,int(length)-1,4):d.tube('silver',pt(u,.1,.15),pt(u,.1,3.1),.055,5)
                if typ=='office' and h>40 and length<80:
                    d.tint=(.82,.9,.98,1)
                    for u in range(2,int(length)-1,4):
                        d.face('silver',[pt(u-.055,.1,3.3),pt(u+.055,.1,3.3),pt(u+.055,.1,h),pt(u-.055,.1,h)])
                        d.face('steel',[pt(u,.1,3.3),pt(u,.4,3.3),pt(u,.4,h),pt(u,.1,h)])
                if typ=='residential' and 10<h<55 and length<38 and rnd.random()<.22:
                    balconies+=1
                    for level in range(5,min(17,int(h)-1),3):
                        for u in range(2,int(length)-2,7):
                            d.tint=tint;d.face('concrete',[pt(u-1.25,.05,level),pt(u+1.25,.05,level),pt(u+1.25,.72,level),pt(u-1.25,.72,level)])
                            d.tint=(.65,.71,.76,1);d.face('steel',[pt(u-1.25,.72,level),pt(u+1.25,.72,level),pt(u+1.25,.72,level+.58),pt(u-1.25,.72,level+.58)])
                            d.face('silver',[pt(u-1.25,.71,level+.58),pt(u+1.25,.71,level+.58),pt(u+1.25,.75,level+.64),pt(u-1.25,.75,level+.64)])
                            for off in [-1.25,1.25]:d.face('silver',[pt(u+off-.015,.72,level),pt(u+off+.015,.72,level),pt(u+off+.015,.72,level+.61),pt(u+off-.015,.72,level+.61)])
                d.tint=tint
        for tri in row['roofTriangles']:
            p,q,r=tri
            if (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])<0:tri=list(reversed(tri))
            b.face('roof',[(x,z,roof) for x,z in tri])
        floors.append({'id':row['id'],'ringsSha256':hashlib.sha256(json.dumps(rings,separators=(',',':')).encode()).hexdigest(),'baseYGame':base,'mainRoofYGame':roof,'visualMaximumYGame':maximum})
        if index%5000==0:print('facade buildings',index,'/',len(buildings),flush=True)
    flush();output.mkdir(parents=True);cm.O=output;assets=[]
    for name,obs in objects.items():
        cm.bpy.ops.object.select_all(action='DESELECT')
        for ob in obs:ob.select_set(True)
        cm.bpy.context.view_layer.objects.active=obs[0]
        cm.bpy.ops.export_scene.gltf(filepath=str(output/(name+'.glb')),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_yup=True,export_vertex_color='NAME',export_vertex_color_name='Color',export_all_vertex_colors=False)
        record={'file':name+'.glb','bytes':(output/(name+'.glb')).stat().st_size,'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in obs),'meshes':len(obs),'sha256':sha(output/(name+'.glb'))};assets.append(record)
        for ob in obs:
            mesh=ob.data;cm.bpy.data.objects.remove(ob,do_unlink=True)
            if not mesh.users:cm.bpy.data.meshes.remove(mesh)
    fp=output/'building-floors.json';fp.write_text(json.dumps(floors,separators=(',',':')))
    report={'kind':'actual-Hangzhou-facade-candidate','cityId':'hangzhou','ordinaryBuildingParts':len(buildings),'sourceBuildingParts':source_count,'smokeSubset':bool(a.limit_buildings),'courtyardHolesRetained':holes,'balconyFacades':balconies,'assets':assets,'floorRecordsSha256':sha(fp),
        'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [source/'manifest.json',bp,ROOT/'scripts/build_city_facades.py',ROOT/'scripts/city_mesh.py',Path(__file__)]},'elapsedSeconds':time.monotonic()-began,
        'status':'exported candidate; not integrated/visually accepted','units':'existing game metres, no second scale','pending':['near detail collision/road clearance','roof and parapet collision heights','roof equipment and ambient occlusion','landmark/base exclusion final binding','actual three-view/day/night/performance']}
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1:])
