"""Decode every H.264 frame and inspect MP4 timing, tracks and loop continuity."""
import argparse,json,struct,subprocess
from pathlib import Path
import numpy as np
from prepare_hangzhou_loading_media import atoms,sha,ROOT

def children(data,parent):
    start,size,header,_=parent
    return list(atoms(data,start+header,start+size))

def metadata(data):
    top=list(atoms(data));moov=next(x for x in top if x[3]==b'moov');tracks=[]
    for trak in [x for x in children(data,moov) if x[3]==b'trak']:
        parts=children(data,trak);tkhd=next(x for x in parts if x[3]==b'tkhd')
        width,height=struct.unpack_from('>II',data,tkhd[0]+tkhd[1]-8)
        mdia=next(x for x in parts if x[3]==b'mdia');mp=children(data,mdia)
        handler=next(x for x in mp if x[3]==b'hdlr');kind=data[handler[0]+handler[2]+8:handler[0]+handler[2]+12].decode('ascii')
        mdhd=next(x for x in mp if x[3]==b'mdhd');body=mdhd[0]+mdhd[2];version=data[body]
        if version==0:timescale,duration=struct.unpack_from('>II',data,body+12)
        elif version==1:
            timescale=struct.unpack_from('>I',data,body+20)[0];duration=struct.unpack_from('>Q',data,body+24)[0]
        else:raise ValueError('Unknown media header version')
        minf=next(x for x in mp if x[3]==b'minf');stbl=next(x for x in children(data,minf) if x[3]==b'stbl');sp=children(data,stbl)
        stsd=next(x for x in sp if x[3]==b'stsd');codec=data[stsd[0]+stsd[2]+12:stsd[0]+stsd[2]+16].decode('ascii')
        stts=next(x for x in sp if x[3]==b'stts');body=stts[0]+stts[2];count=struct.unpack_from('>I',data,body+4)[0]
        rows=[struct.unpack_from('>II',data,body+8+i*8) for i in range(count)]
        samples=sum(n for n,dt in rows);ticks=sum(n*dt for n,dt in rows)
        tracks.append({'kind':kind,'width':width/65536,'height':height/65536,'codec':codec,'timescale':timescale,
                       'durationSeconds':duration/timescale,'samples':samples,'sampleDurationTicks':ticks,'fps':samples/(ticks/timescale)})
    return tracks,moov[0]<next(x[0] for x in top if x[3]==b'mdat')

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--decoder',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=(ROOT/a.source).resolve();out=(ROOT/a.output).resolve();decoder=(ROOT/a.decoder).resolve()
    if out.exists():raise ValueError('Fresh review directory required')
    binding=json.loads(decoder.read_text());binary=ROOT/binding['binary']
    if sha(binary)!=binding['binarySha256']:raise ValueError('Changed native decoder')
    asset=json.loads((source/'asset-manifest.json').read_text());movie=source/'hangzhou-clay-loop.mp4'
    if sha(movie)!=asset['files'][movie.name]['sha256']:raise ValueError('Changed actual movie')
    tracks,progressive=metadata(movie.read_bytes());video=[t for t in tracks if t['kind']=='vide'];assert len(video)==1
    v=video[0];out.mkdir(parents=True);selected=[0,1,180,360,540,718,719];frames={};count=0;frame_bytes=320*180*3
    command=[str(binary),'-hide_banner','-v','error','-i',str(movie),'-an','-vf','scale=320:180','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    with (out/'decode.log').open('wb') as errors:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors)
        while True:
            data=child.stdout.read(frame_bytes)
            if not data:break
            while len(data)<frame_bytes:
                rest=child.stdout.read(frame_bytes-len(data))
                if not rest:raise ValueError('Partial decoded frame')
                data+=rest
            if count in selected:frames[count]=np.frombuffer(data,dtype='u1').copy()
            count+=1
        if child.wait()!=0:raise ValueError('Movie decode failed')
    difference=lambda a,b:float(np.abs(frames[a].astype('i2')-frames[b]).mean())
    first,last,seam=difference(0,1),difference(718,719),difference(719,0)
    expression='+'.join('eq(n\\,'+str(n)+')' for n in selected)
    subprocess.run([str(binary),'-hide_banner','-v','error','-i',str(movie),'-vf','select='+expression,'-vsync','0','-q:v','2',str(out/'frame-%03d.jpg')],check=True)
    checks={'h264':v['codec']=='avc1','fullHD':(v['width'],v['height'])==(1920,1080),'fps30':abs(v['fps']-30)<1e-8,
            'seconds24':abs(v['durationSeconds']-24)<1e-8,'all720FramesDecoded':count==v['samples']==720,
            'silent':not any(t['kind']=='soun' for t in tracks),'metadataBeforeMedia':progressive,
            'all7PreviewFramesPresent':len(list(out.glob('frame-*.jpg')))==7,
            'seamComparableToAdjacentFrames':seam<=max(first,last)*2+.1}
    result={'kind':'actual offline movie decode; not browser or in-game acceptance','inputs':{str(p.relative_to(ROOT)):sha(p) for p in [movie,source/'asset-manifest.json',decoder,Path(__file__)]},
            'tracks':tracks,'decodedFrames':count,'previewSourceFrames':selected,'pixelMeanAbsoluteDifferenceAt320x180':{'firstAdjacent':first,'lastAdjacent':last,'loopSeam':seam},
            'checks':checks,'pass':all(checks.values()),'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},
            'pending':['visual review of decoded views','actual loading UI/autoplay/fallback/reduced-motion browser validation']}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)
if __name__=='__main__':main()
