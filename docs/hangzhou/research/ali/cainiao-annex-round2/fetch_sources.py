"""Archive public evidence and fail honestly; pictures never become textures."""
import hashlib,json,sys
from pathlib import Path
from urllib.request import Request,urlopen
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
SOURCES=[
('yuhang-home','https://www.yuhang.gov.cn/','杭州市余杭区政府','government','current','Discover original publicplanning portal/search entry'),
('phase1-usechange-repost','https://www.sohu.com/a/774528858_121123899','小易看财经 / 来源杭州建设规划','republication ofpublicnotice, originalgovpagepending','2024-04-26','Publicnotice7buildings/masterplanlead; not callrepostofficialoriginal'),
('phase2-usechange-repost','https://www.sohu.com/a/911920489_121123899','小易看财经 / 来源杭州建设规划','republication ofpublicnotice, originalgovpagepending','2025-07-08','Publicnotice/masterplanlead; exactoriginalURLpending'),
('zjol-phase2-2019','https://zzhz.zjol.com.cn/ycpd/jrbd/201910/t20191014_11186217.shtml','浙江在线 / originalreporter叶迪','original reportingwithpublicnoticescreenshots','2019-10-14','10plannedbuildings+62463m² projectepoch, notasbuiltcount'),
('hangzhou-official-2023','https://www.ehangzhou.gov.cn/2023-04/20/c_284481.htm','Hangzhou government officialcitynews','government','2023-04-20','HQopening andcomplexscope'),
('chicago-award-2024','https://www.chicagoathenaeum.org/international-architecture-award-winners-2024/2024/08/16/cainiao-headquarters-hangzhou%2C-china-2022/','The Chicago Athenaeum / architectsubmission','originalawardprojectsubmission','2024-08-16 / project2022','Potentialpublishedplansandcomponentprogram'),
('aedas-archinect-2023','https://archinect.com/firms/project/6259264/aedas-completed-cainiao-headquarters-with-high-connectivity-and-adaptability/150377553','Aedas firmprojectonArchinect','architect','2023','Completedphotos/possibleplan'),
('yuhang-road-eia','https://www.yuhang.gov.cn/module/download/downfile.jsp?classid=0&filename=dcf66d02456a4fbc922d18681a5a7911.pdf','余杭区政府','government project EIA','unknown','Nearbyroadsandsiteplan coordinate/context, notbuildingfootprintunlessdrawingexplicit'),
('hangzhou-2021-projects','https://drc.hangzhou.gov.cn/module/download/downfile.jsp?classid=0&filename=6e8eca764de94288b89ca80560df111a.pdf','杭州市发改委','government','2021','Formalprojectnames/codes/scales noautomaticparcelperiodassignment'),
]
def main():
    folder=HERE/'references';folder.mkdir(exist_ok=True);rows=[]
    for sid,url,publisher,authority,date,use in SOURCES:
        if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
        p=folder/(sid+('.pdf' if '.pdf' in url else '.html'));r={'id':sid,'url':url,'publisher':publisher,'authority':authority,'sourceDate':date,'use':use,'accessedAt':'2026-10-14',
            'license':'Copyright retained; referenceonly; no runtimeimage orredistribution license verified'}
        try:
            with urlopen(Request(url,headers={'User-Agent':'GTA_HZ-source-evidence/1.0'}),timeout=20) as response:data=response.read();r.update(finalUrl=response.geturl(),contentType=response.headers.get('Content-Type'))
            if len(data)<200:raise ValueError('tinyresponse')
            p.write_bytes(data);r.update(status='downloaded',localPath=str(p.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        except Exception as error:r.update(status='failed',error=str(error),localPath=None)
        rows.append(r);print(json.dumps({'id':sid,'status':r['status'],'bytes':r.get('bytes'),'error':r.get('error')},ensure_ascii=False),flush=True)
    file=folder/('fetches-'+('-'.join(sys.argv[1:]) if len(sys.argv)>1 else 'all')+'.json');file.write_text(json.dumps({'sources':rows},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
