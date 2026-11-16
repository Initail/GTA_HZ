"""Offline clay loading film from actual Hangzhou candidate geometry.

Use a factory-startup Blender process. This is presentation media, never an
in-game screenshot, browser result or proof that the playable city is ready.
"""
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--engine', choices=['BLENDER_WORKBENCH', 'BLENDER_EEVEE'], default='BLENDER_EEVEE')
    a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
    out = (ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents: raise ValueError('Fresh artifact directory required')
    out.mkdir(parents=True)
    started = time.monotonic(); inputs = {}
    def bind(path):
        path = ROOT/path; inputs[str(path.relative_to(ROOT))] = sha(path); return path
    delivery_path = bind('artifacts/cities/hangzhou/landmark-floor-transforms-v1/hangzhou-gate/model-delivery.json')
    delivery = json.loads(delivery_path.read_text())
    spec = json.loads(bind(delivery['spec']).read_text())
    geography = json.loads(bind('config/cities/hangzhou.json').read_text())['geography']
    center = np.array([*delivery['anchorGame'], 0.])
    first, second = [t['centroidWGS84'] for t in spec['towers']]
    # Start perpendicular to the actual tower axis so the twin towers and
    # arched connection are visible rather than occluding one another.
    de=(second[0]-first[0])*geography['eastMetresPerDegree']
    dn=(second[1]-first[1])*geography['northMetresPerDegree']
    start_angle=math.atan2(dn,-de)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for relative in [delivery['artifact'], 'artifacts/cities/hangzhou/base-glb-v5/buildings.glb',
                     'artifacts/cities/hangzhou/landmark-foundations-glb-v4/landmark-foundations.glb']:
        path = bind(relative)
        if relative == delivery['artifact'] and sha(path) != delivery['artifactSha256']: raise ValueError('Changed gate')
        bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    for ob in list(bpy.data.objects):
        if ob.type != 'MESH': continue
        world = np.asarray([ob.matrix_world @ Vector(v) for v in ob.bound_box])
        closest = np.maximum(world.min(axis=0)[:2]-center[:2], np.maximum(center[:2]-world.max(axis=0)[:2], 0))
        if np.linalg.norm(closest) > 950: bpy.data.objects.remove(ob, do_unlink=True)
    # Exact prepared source triangles around this presentation set. Importing
    # the full 4.8M-face terrain is unnecessary for a bounded loading film.
    prepared = ROOT/'artifacts/cities/hangzhou/render-meshes-v9'
    manifest = json.loads(bind(str((prepared/'manifest.json').relative_to(ROOT))).read_text())
    for record in manifest['meshRecords']:
        if not record['name'].startswith('terrain_'): continue
        ix, iz = map(int, record['name'].rsplit('_', 2)[-2:])
        tile_center = np.array([(ix+.5)*640, (iz+.5)*640])
        if np.linalg.norm(np.maximum(np.abs(tile_center-center[:2])-320, 0)) > 950: continue
        path = bind(str((prepared/record['file']).relative_to(ROOT)))
        if sha(path) != record['sha256']: raise ValueError('Changed terrain')
        with np.load(path) as data:
            for material in data.files:
                triangles = data[material]
                mesh = bpy.data.meshes.new(record['name']+'_'+material)
                flat = (triangles-center).astype('f4').reshape(-1,3)
                mesh.vertices.add(len(flat)); mesh.vertices.foreach_set('co', flat.ravel())
                mesh.loops.add(len(flat)); mesh.loops.foreach_set('vertex_index', np.arange(len(flat), dtype='i4'))
                mesh.polygons.add(len(triangles)); mesh.polygons.foreach_set('loop_start', np.arange(0,len(flat),3,dtype='i4'))
                mesh.polygons.foreach_set('loop_total', np.full(len(triangles),3,dtype='i4')); mesh.update()
                ob = bpy.data.objects.new(mesh.name, mesh); bpy.context.collection.objects.link(ob)
                ob.location = center
    colors = {'stone': (.73,.70,.61,1), 'glass': (.32,.49,.53,1), 'land': (.46,.49,.40,1),
              'park': (.38,.47,.33,1), 'water': (.12,.32,.37,1), 'silver': (.86,.82,.70,1)}
    mats = {}
    for name, color in colors.items():
        m = bpy.data.materials.new('loading-'+name); m.diffuse_color=color; m.use_nodes=True
        bsdf=m.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value=color
        bsdf.inputs['Roughness'].default_value=.7 if name!='water' else .28
        mats[name]=m
    visible=[]
    for ob in bpy.data.objects:
        if ob.type!='MESH': continue
        old=[m.name.lower() if m else '' for m in ob.data.materials]
        names=old or [ob.name.lower()]
        chosen=[]
        for name in names:
            kind=next((k for k in ['water','park','glass','silver','land'] if k in name),'stone')
            chosen.append(mats[kind])
        ob.data.materials.clear()
        for m in chosen: ob.data.materials.append(m)
        visible.append({'name':ob.name,'triangles':sum(len(poly.vertices)-2 for poly in ob.data.polygons)})
    scene=bpy.context.scene; scene.render.engine=a.engine
    scene.render.resolution_x=960 if a.preview else 1920
    scene.render.resolution_y=540 if a.preview else 1080
    scene.render.resolution_percentage=100; scene.render.fps=30
    scene.world.color=(.4,.5,.6)
    scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.63,.72,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.55
    scene.view_settings.view_transform='AgX'
    sun=bpy.data.lights.new('loading-sun','SUN'); sun.energy=3.; sun.angle=math.radians(12)
    sunob=bpy.data.objects.new('loading-sun',sun); scene.collection.objects.link(sunob)
    sunob.rotation_euler=(math.radians(25),math.radians(-30),math.radians(-30))
    # Babylon's original loading set uses .87 radians vertical FOV. Blender
    # specifies a horizontal 36mm sensor, so 22mm matches that at 16:9.
    cam=bpy.data.cameras.new('loading-camera'); cam.lens=22; cam.clip_start=.5; cam.clip_end=2200
    camera=bpy.data.objects.new('loading-camera',cam); scene.collection.objects.link(camera); scene.camera=camera
    poses=[]
    for frame in range(721):
        angle=start_angle+frame/720*math.tau
        position=Vector((center[0]+math.sin(angle)*365,center[1]+math.cos(angle)*365,195))
        right=Vector((-math.cos(angle),math.sin(angle),0))
        target=Vector((center[0],center[1],85))-right*55
        camera.location=position; camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler()
        camera.keyframe_insert(data_path='location',frame=frame+1); camera.keyframe_insert(data_path='rotation_euler',frame=frame+1)
        poses.append({'frame':frame,'eyeENU':list(position),'targetENU':list(target)})
    # Render exact frame poses, including the duplicated endpoint only as a
    # mathematical loop check. The encoded movie uses [0,720), never frame721.
    scene.frame_start=1; scene.frame_end=720
    scene.frame_set(1); scene.render.image_settings.file_format='JPEG'; scene.render.image_settings.quality=94
    scene.render.filepath=str(out/'hangzhou-clay-poster.jpg'); bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'loading-scene.blend'))
    if not a.preview:
        # Blender 5's media_type selects the format enum's image/video branch.
        # See projects.blender.org/blender/blender/issues/152175.
        scene.render.image_settings.media_type='VIDEO'
        scene.render.image_settings.file_format='FFMPEG'; scene.render.ffmpeg.format='MPEG4'; scene.render.ffmpeg.codec='H264'
        scene.render.ffmpeg.constant_rate_factor='MEDIUM'; scene.render.ffmpeg.audio_codec='NONE'; scene.render.ffmpeg.ffmpeg_preset='GOOD'
        scene.render.ffmpeg.maxrate=2200; scene.render.ffmpeg.gopsize=30
        scene.render.filepath=str(out/'hangzhou-clay-loop.mp4'); bpy.ops.render.render(animation=True)
        movies=list(out.glob('*.mp4'))
        if len(movies)!=1:raise ValueError('Expected one encoded loading movie')
        if movies[0].name!='hangzhou-clay-loop.mp4':movies[0].rename(out/'hangzhou-clay-loop.mp4')
    report={'kind':'offline clay loading presentation; not an in-game capture','cityId':'hangzhou','inputs':inputs,
            'rendererSha256':sha(Path(__file__)),'engine':a.engine,'previewOnly':a.preview,'width':scene.render.resolution_x,
            'height':scene.render.resolution_y,'fps':30,'frames':720,'seconds':24,'audio':False,'visible':visible,
            'poses':poses,'durationCpuSeconds':time.monotonic()-started,
            'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},
            'pending':['visual review of actual offline film','encoded duration/frame count/seam checks','real loading UI/autoplay/fallback browser check']}
    (out/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['visible','poses','inputs','files']},indent=2))

if __name__=='__main__': main()
