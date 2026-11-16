"""Original WGS84 source diagrams, not actual game acceptance screenshots."""
import hashlib,importlib.util,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
r=importlib.util.spec_from_file_location('metrics',HERE.parent/'measure_osm.py');measure=importlib.util.module_from_spec(r);r.loader.exec_module(measure)
def points(c):
    if isinstance(c[0],(int,float)):return [c]
    return [p for row in c for p in points(row)]

def main():
    src=json.loads((HERE/'fixed-source-objects.json').read_text());sites=src['sites'];old=json.loads((HERE.parent/'alibaba-a-round2/spec.json').read_text());oldids=set(old['baseBuildingIdsToExclude']);saved=[]
    for name,ids,title in [('alibaba-a',['way/645135612'],'A source coverage: blue = round2, orange = blocked A9'),
            ('cainiao',['way/1228913717','way/1293416973','way/1293548829'],'Cainiao coverage: physical buildings absent from mapped dataset are NOT absent in reality')]:
        polygons=[sites[i]['parcel']['geometry']['coordinates'][0][0] for i in ids];ps=[p for poly in polygons for p in poly];origin=[sum(p[0] for p in ps)/len(ps),sum(p[1] for p in ps)/len(ps)];local=[measure.enu(p,origin) for p in ps];xmin,ymin=min(p[0] for p in local),min(p[1] for p in local);xmax,ymax=max(p[0] for p in local),max(p[1] for p in local);zoom=min(1020/(xmax-xmin),580/(ymax-ymin))
        def xy(p):
            x,y=measure.enu(p,origin);return (60+(x-xmin)*zoom,670-(y-ymin)*zoom)
        image=Image.new('RGB',(1140,790),(243,246,244));d=ImageDraw.Draw(image);font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20);small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',14)
        d.text((24,18),title,font=font,fill=(20,41,48));d.text((24,49),'Fixed Geofabrik EPSG:4326; ENU metres. Volunteer geometry accuracy unknown; no game/export/visual pass.',font=small,fill=(57,73,80))
        for sid in ids:
            poly=sites[sid]['parcel']['geometry']['coordinates'][0][0];d.polygon([xy(p) for p in poly],fill=(228,236,219),outline=(94,121,81),width=2)
            rp=sites[sid]['metrics']['bboxCenterWGS84'];d.text(xy(rp),sid,font=small,fill=(85,100,72))
        seen=set()
        for sid in ids:
            for f in sites[sid]['layers']['roads']:
                if f['id'] in seen:continue
                seen.add(f['id']);tag=f['properties']['tags'];color=(145,169,170) if tag.get('highway')=='footway' else (150,151,148)
                if tag.get('bridge'):color=(114,78,123)
                if f['geometry']['type']=='LineString':d.line([xy(p) for p in f['geometry']['coordinates']],fill=color,width=2)
            for f in sites[sid]['layers']['buildings']:
                color=(237,174,77) if f['id']=='way/456731145' else (136,183,210) if f['id'] in oldids else (154,184,159) if f['id']=='way/1355173307' else (208,210,212)
                for poly in f['geometry']['coordinates']:
                    d.polygon([xy(p) for p in poly[0]],fill=color,outline=(67,85,91),width=1)
                    for hole in poly[1:]:d.polygon([xy(p) for p in hole],fill=(228,236,219),outline=(67,85,91))
                allp=points(f['geometry']['coordinates']);center=[sum(p[0] for p in allp)/len(allp),sum(p[1] for p in allp)/len(allp)]
                links={'way/642355050':'L1','relation/6752593':'L2','relation/6752573':'L3','relation/6750408':'L4'}
                label=links.get(f['id']) or f['properties']['tags'].get('name:en')
                if f['id']=='way/1355173307':label='HQ way/1355173307'
                if label:d.text(xy(center),label,font=small,fill=(33,46,53))
        d.line([(950,110),(950,85)],fill=(41,68,72),width=3);d.polygon([(944,90),(956,90),(950,78)],fill=(41,68,72));d.text((969,88),'N',font=font,fill=(41,68,72))
        d.line([(60,714),(60+200*zoom,714)],fill=(41,68,72),width=3);d.text((60,722),'200 real metres',font=small,fill=(41,68,72));d.text((24,760),'CPU source plan only. New extension module not created; no new source IDs excluded.',font=small,fill=(57,73,80))
        out=HERE/('source-coverage-'+name+'.png');image.save(out);saved.append({'path':str(out.relative_to(ROOT)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'actualGameScreenshot':False})
    (HERE/'source-diagram-manifest.json').write_text(json.dumps({'sourcePbfSha256':src['source']['sha256'],'diagrams':saved},indent=2)+'\n');print('Saved2sourcecoverage diagrams, notmodelpreviews')
if __name__=='__main__':main()
