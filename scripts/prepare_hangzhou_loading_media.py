"""Move MP4 metadata before media bytes for progressive loading; no re-encode.

Only stco/co64 chunk offsets change. Verify every media payload byte afterward.
The original Blender output and failed candidates remain untouched.
"""
import argparse, hashlib, json, shutil, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def atoms(data, start=0, end=None):
    end=len(data) if end is None else end
    while start<end:
        if end-start<8:raise ValueError('Truncated MP4 atom')
        size,kind=struct.unpack_from('>I4s',data,start);header=8
        if size==1:
            if end-start<16:raise ValueError('Truncated extended atom')
            size=struct.unpack_from('>Q',data,start+8)[0];header=16
        elif size==0:size=end-start
        if size<header or start+size>end:raise ValueError('Invalid atom extent')
        yield start,size,header,kind
        start+=size

def faststart(data):
    top=list(atoms(data));moovs=[a for a in top if a[3]==b'moov'];mdats=[a for a in top if a[3]==b'mdat']
    if len(moovs)!=1 or not mdats:raise ValueError('Unfragmented MP4 with one moov required')
    if any(a[3] in (b'moof',b'sidx') for a in top):raise ValueError('Fragmented MP4 not handled')
    moov=moovs[0];first=mdats[0][0]
    if moov[0]<first:return data,0
    replacement=bytearray(data[moov[0]:moov[0]+moov[1]]);changed=0
    def patch(start,end):
        nonlocal changed
        for offset,size,header,kind in atoms(replacement,start,end):
            body=offset+header
            if kind in (b'moov',b'trak',b'mdia',b'minf',b'stbl',b'udta',b'edts',b'dinf'):
                patch(body,offset+size)
            elif kind in (b'stco',b'co64'):
                if body+8>offset+size:raise ValueError('Truncated chunk table')
                count=struct.unpack_from('>I',replacement,body+4)[0];width=4 if kind==b'stco' else 8;fmt='>I' if width==4 else '>Q'
                if body+8+count*width!=offset+size:raise ValueError('Invalid chunk table length')
                for i in range(count):
                    at=body+8+i*width;value=struct.unpack_from(fmt,replacement,at)[0]
                    if not any(s+h<=value<s+n for s,n,h,_ in mdats):raise ValueError('Chunk offset outside media data')
                    new=value+moov[1] if first<=value<moov[0] else value
                    if width==4 and new>=2**32:raise ValueError('Offset would require co64 migration')
                    struct.pack_into(fmt,replacement,at,new);changed+=new!=value
    patch(0,len(replacement))
    output=[]
    for start,size,header,kind in top:
        if start==first:output.append(bytes(replacement))
        if kind!=b'moov':output.append(data[start:start+size])
    result=b''.join(output)
    old_media=[data[s+h:s+n] for s,n,h,k in top if k==b'mdat']
    new_media=[result[s+h:s+n] for s,n,h,k in atoms(result) if k==b'mdat']
    if old_media!=new_media or len(data)!=len(result):raise ValueError('Faststart changed media payload')
    return result,changed

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=(ROOT/a.source).resolve();out=(ROOT/a.output).resolve()
    if out.exists() or ROOT/'artifacts' not in out.parents:raise ValueError('Fresh candidate required')
    report=json.loads((source/'source.json').read_text())
    if report['cityId']!='hangzhou' or report['previewOnly']:raise ValueError('Actual Hangzhou movie required')
    movie=source/'hangzhou-clay-loop.mp4';poster=source/'hangzhou-clay-poster.jpg'
    for asset in [movie,poster]:
        if report['files'][asset.name]!=sha(asset):raise ValueError('Changed encoded media')
    result,changed=faststart(movie.read_bytes());out.mkdir(parents=True)
    (out/movie.name).write_bytes(result);shutil.copy2(poster,out/poster.name)
    top=[{'type':k.decode('ascii'),'offset':s,'bytes':n} for s,n,h,k in atoms(result)]
    assert next(x['offset'] for x in top if x['type']=='moov')<next(x['offset'] for x in top if x['type']=='mdat')
    delivery={'cityId':'hangzhou','kind':'offline loading-media candidate; encoded content preserved',
              'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [movie,poster,source/'source.json',Path(__file__)]},
              'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in out.iterdir()},
              'atoms':top,'changedChunkOffsets':changed,'mediaPayloadBytesIdentical':True,
              'license':'MIT for project-authored geometry/scripts; OSM-derived surrounding data remains ODbL with original attribution',
              'sourceAttribution':'© OpenStreetMap contributors; fixed Zhejiang source snapshot documented in city data provenance',
              'pending':['native decode/frame-count/loop/visual review','real browser loading/autoplay/failure/reduced-motion checks']}
    (out/'asset-manifest.json').write_text(json.dumps(delivery,indent=2)+'\n');print(json.dumps(delivery,indent=2))

if __name__=='__main__':main()
