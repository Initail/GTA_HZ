"""Split an offline RGBA data bake into two opaque PNGs for Canvas-safe loading.
Runtime combines RGB visibility and grayscale ground into one RGBA texture.
"""
import argparse,json,struct,zlib,hashlib
from pathlib import Path
import numpy as np
import rasterio
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def png(data):
    h,w,c=data.shape
    def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    header=struct.pack('>IIBBBBB',w,h,8,2 if c==3 else 0,0,0,0)
    rows=np.zeros((h,w*c+1),dtype=np.uint8);rows[:,1:]=data.reshape(h,w*c)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',header)+chunk(b'IDAT',zlib.compress(rows.tobytes(),9))+chunk(b'IEND',b'')
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();source=ROOT/a.input;out=(ROOT/a.output).resolve()
    if ROOT/'artifacts' not in out.parents or out.exists():raise ValueError('Fresh candidate required')
    report=json.loads((source/'manifest.json').read_text());meta=json.loads((source/'occlusion.json').read_text())
    for f,record in report['files'].items():
        if sha(source/f)!=record['sha256']:raise ValueError('Changed bake '+f)
    with rasterio.open(source/'occlusion.png') as dataset:raw=dataset.read()
    if raw.dtype!=np.uint8 or raw.shape!=(4,meta['height'],meta['width']):raise ValueError('Wrong RGBA bake')
    out.mkdir(parents=True);(out/'occlusion.png').write_bytes(png(raw[:3].transpose(1,2,0)));(out/'ground-height.png').write_bytes(png(raw[3:].transpose(1,2,0)))
    meta['groundFile']='ground-height.png';meta['channels']='Opaque RGB visibility and separate opaque R8 ground, combined into a single RGBA data texture at load'
    (out/'occlusion.json').write_text(json.dumps(meta,indent=2)+'\n')
    for f,expected in [('occlusion.png',raw[:3]),('ground-height.png',raw[3:])]:
        with rasterio.open(out/f) as dataset:
            if not np.array_equal(dataset.read(),expected):raise ValueError('PNG changed raster data')
    result={**report,'kind':'opaque-PNG-packed-ambient-candidate','inputManifest':a.input+'/manifest.json','inputManifestSha256':sha(source/'manifest.json'),'packerSha256':sha(Path(__file__)),'pixelParityPassed':True,'files':{f.name:{'sha256':sha(f),'bytes':f.stat().st_size} for f in out.iterdir()},'status':'offline bytes verified; actual browser material and memory acceptance pending'}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
