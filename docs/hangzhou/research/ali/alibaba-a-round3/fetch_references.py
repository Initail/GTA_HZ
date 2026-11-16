"""Read-only public evidence snapshots; no game assets or shared edits."""
import hashlib,json,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
HERE=Path(__file__).resolve().parent
SOURCES=[
 ('cloud-tour-2024','https://resource.alibabacloud.com/event/detail?id=6370','Alibaba Cloud','owner event itinerary','2024-03-13','No.9 Hall visiting; A5 gate and A visitor center are distinct place descriptions'),
 ('carec-tour-2023','https://www.carecprogram.org/uploads/CIN-Conference-Handbook-Print.pdf','CAREC / Asian Development Bank','official conference organizer','2023-11-22/24','No.9 Hall program and2016 construction/2022 contents renewal reported, noWGS84footprint'),
 ('sentiment-hall9','https://www.sentimenthifi.com/c_s.asp?cid=71','Sentiment影音','project audiovisual contractor','unknown','Southeast-by-water ship silhouette; no A9 sourcepolygon identification'),
 ('ceibs-tour-2014','https://cn.ceibs.edu/agri-food-business-association20141122','CEIBS','visit organizer','2014-11-22','Historical6office/2parking/9Hall underconstruction report; not presentA1-A9crosswalk'),
 ('w3c-visitor-2018','https://www.w3.org/wiki/AB/2018-03-Hangzhou','W3C','meeting organizer','2018-03-13/14','HistoricBuilding5visitorcenter address; no currentfloorplan confirmation'),
 ('artunit-visitor','https://www.artunit.cn/pages/albb.html','ARTUNIT','signage design supplier','2019 project perpublication','Exterior/interior signage project; precise modernmappedidentity unknown'),
 ('aedas-industry-2020','https://www.archina.com/index.php?a=show&g=works&id=5118&m=index','Aedas published on ARCHINA','architect supplied project','2020-04-14','HQphase1 and industryphase1/2 program; publishedrenders distinguishedfromcompletedphotos'),
 ('a9-osm-history','https://api.openstreetmap.org/api/0.6/way/456731145/history','OpenStreetMap contributors','volunteered map history','various','History ofmapped A9labels/levels, not surveyed identity orheight'),
]

def main():
    (HERE/'references').mkdir(exist_ok=True)
    records=[]
    for sid,url,publisher,authority,date,use in SOURCES:
        if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
        ext='.pdf' if '.pdf' in url else '.osm' if sid.endswith('history') else '.html';out=HERE/'references'/(sid+ext)
        record={'id':sid,'url':url,'publisher':publisher,'authority':authority,'sourceDate':date,'use':use,'accessedAt':'2026-10-14',
            'license':'ODbL-1.0' if sid.endswith('history') else 'Copyright retained; reference only, no redistribution or runtime texture license verified'}
        try:
            with urlopen(Request(url,headers={'User-Agent':'GTA_HZ-evidence-research/1.0'}),timeout=22) as response:
                data=response.read();record.update(finalUrl=response.geturl(),contentType=response.headers.get('Content-Type'))
            if len(data)<200:raise ValueError('Insufficientresponsebytes')
            out.write_bytes(data);record.update(status='downloaded',localPath=str(out.relative_to(HERE.parents[4])),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        except Exception as error:record.update(status='failed',error=str(error),localPath=None)
        records.append(record);print(json.dumps({'id':sid,'status':record['status'],'bytes':record.get('bytes'),'error':record.get('error')},ensure_ascii=False),flush=True)
    dest=HERE/'references'/('fetches-'+('-'.join(sys.argv[1:]) if len(sys.argv)>1 else 'all')+'.json')
    dest.write_text(json.dumps({'sources':records},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
