"""Stream a bounded WGS84 feature window from an existing GeoJSON snapshot.

No geocoder or projection is used. Original features and source hash are retained.
The parser holds one feature/window, not the entire city feature collection.
"""
import argparse,hashlib,json,re
from pathlib import Path
def features(path):
    decoder=json.JSONDecoder()
    with path.open(encoding='utf-8') as source:
        buffer=source.read(65536)
        match=re.search(r'"features"\s*:\s*\[',buffer)
        if not match:raise ValueError('FeatureCollection array not found in header')
        cursor=match.end()
        while True:
            while cursor<len(buffer) and buffer[cursor] in ' \t\r\n,':cursor+=1
            if cursor<len(buffer) and buffer[cursor]==']':return
            try:feature,end=decoder.raw_decode(buffer,cursor)
            except json.JSONDecodeError:
                more=source.read(65536)
                if not more:raise ValueError('Truncated GeoJSON feature')
                buffer=buffer[cursor:]+more;cursor=0
                if len(buffer)>8*1024*1024:raise ValueError('Single source feature exceeds parser budget')
                continue
            if not isinstance(feature,dict) or feature.get('type')!='Feature':raise ValueError('Invalid GeoJSON feature')
            yield feature;cursor=end
            if cursor>=65536:buffer=buffer[cursor:];cursor=0
def coordinates(value):
    if value and isinstance(value[0],(int,float)):yield value
    else:
        for member in value:yield from coordinates(member)
def in_window(feature,bbox):
    points=list(coordinates(feature['geometry'].get('coordinates',[])))
    if not points:return False
    xs=[p[0] for p in points];ys=[p[1] for p in points]
    return max(xs)>=bbox[0] and min(xs)<=bbox[2] and max(ys)>=bbox[1] and min(ys)<=bbox[3]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--bbox',nargs=4,type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit('Choose a new output; existing evidence is protected.')
    selected=[f for f in features(a.source) if in_window(f,a.bbox)]
    digest=hashlib.sha256()
    with a.source.open('rb') as source:
        for chunk in iter(lambda:source.read(65536),b''):digest.update(chunk)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'type':'FeatureCollection','source':str(a.source),'sourceSha256':digest.hexdigest(),'bboxWGS84':a.bbox,'crs':'EPSG:4326','license':'ODbL-1.0','features':selected},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({'features':len(selected),'bytes':a.output.stat().st_size,'output':str(a.output)}))
if __name__=='__main__':main()
