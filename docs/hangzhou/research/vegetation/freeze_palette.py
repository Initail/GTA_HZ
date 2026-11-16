"""Freeze regional species/scene evidence and estimated procedural prototypes.

This is a local asset family, not a surveyed geographic landmark. No fabricated
WGS84 tree inventory or landmark evidence-ready CLI coordinates are introduced.
"""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,j):
    p=HERE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');return sha(p)

def main():
    sources=[]
    files=[('shade-plan','references/hangzhou-shade-plan.pdf','https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web149/site/attach/0/b10433c8ee784870b09b90f4e9825604.pdf','杭州市林荫道系统专项规划（说明书）','2021-09-07 PDF creation metadata; underlying inventory epoch not verified','杭州政府公开规划资料'),
      ('city-streettrees','references/hangzhou-streettrees.html','https://www.hzzx.gov.cn/content/2022-08/25/content_8337762.htm','绿树成荫夏日凉','2022-08-25','杭州市政协 / 杭州日报'),
      ('fall-color-study','references/hangzhou-fall-color-study.html','https://zlxb.zafu.edu.cn/article/zjnldxxb/2014/4/597','秋色叶树种在杭州行道树中的应用','2014; DOI10.11833/j.issn.2095-0756.2014.04.016','浙江农林大学学报；杨莉莉、刘盈盈原始杭州道路调查'),
      ('osmanthus-experts','references/hangzhou-osmanthus.html','https://www.zafu.edu.cn/info/1012/109766.htm','浙农林大科技团队用科技“预约”杭州桂花按期开放','2023-10-05 university publication; article2023-10-02','浙江农林大学/园林专家访谈'),
      ('westlake-forest-history','references/westlake-forest-history.html','https://www.hzzx.gov.cn/hzzx/content/2010-10/26/content_5139964.htm','建国初期西湖整治和建设纪事','2010-10-26 web publication; retrospective1950s, journal2006section','杭州市政协；冷晓历史记录')]
    for id,name,url,title,date,publisher in files:
        p=HERE/name;assert p.exists()
        sources.append({'id':id,'url':url,'title':title,'publisher':publisher,'sourceDate':date,'accessedAt':'2026-10-14','status':'downloaded-and-read',
            'localPath':str(p.relative_to(ROOT)),'sha256':sha(p),'license':'unknown; source documents/reference pages not runtime textures','use':'species/scene/season descriptions, not exact present tree positions or prototype measurements'})
    sources += [{'id':'unesco-westlake','url':'https://whc.unesco.org/uploads/nominations/1334.pdf','publisher':'China State Party/UNESCO','accessedAt':'2026-10-14','sourceDate':'2011nomination; photos2006',
        'status':'original-read-and-pages-rendered','sha256':'5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442','license':'unknown; reference only',
        'localPath':'docs/hangzhou/research/core/west-lake-causeways-round2/references/unesco-causeway-aerial-p59.png','localSnapshotSha256':sha(ROOT/'docs/hangzhou/research/core/west-lake-causeways-round2/references/unesco-causeway-aerial-p59.png'),
        'use':'traditional intercropped peaches/willows; source page64/75 andprevious source hash, no new lake/plant positions'},
       {'id':'willow-botanical','url':'https://wysgjgy.fujian.gov.cn/zwgk/zwkp/202305/t20230512_6168312.htm','publisher':'武夷山国家公园科研监测中心','accessedAt':'2026-10-14','sourceDate':'2023-05-12',
        'status':'web-read','license':'unknown; no photo assets','use':'Salix babylonica deciduous, narrow leaves and pendent small branches; not Hangzhou inventory'},
       {'id':'plane-flora','url':'https://www.iplant.cn/z/frps/1091','publisher':'中国科学院《中国植物志》在线资料','accessedAt':'2026-10-14','sourceDate':'1979FRPS35(2)',
        'status':'web-read','license':'unknown; no photo assets','use':'Platanaceae pale flaking bark/palmatelylobed leaves/deciduous; explicitly cultivated inChina, not native'},
       {'id':'westlake-adoption','url':'https://www.hangzhou.gov.cn/art/2025/3/10/art_812262_59110191.html','publisher':'杭州市政府 / 西湖景区认养活动资料','accessedAt':'2026-10-14','sourceDate':'2025-03-10',
        'status':'search-extract-only; directfetch403','license':'unknown; no photo assets','use':'district examples: camphor/sweetgum, willow柳浪闻莺, osmanthus满陇桂雨; no precise distribution claim'}]
    dims=[('camphor','香樟','Cinnamomum camphora (regional-source nomenclature)',18,6.8,3.7,5,2.0,'evergreen',['shade-plan','city-streettrees','westlake-forest-history'],'broad-rounded-forked'),
      ('willow','垂柳','Salix babylonica',11,5.0,2.3,3,1.5,'deciduous',['unesco-westlake','willow-botanical'],'arching-pendent'),
      ('osmanthus','桂花','Osmanthus fragrans',5.5,2.6,1.1,1.5,.8,'evergreen',['osmanthus-experts','shade-plan'],'dense-small-rounded'),
      ('ginkgo','银杏','Ginkgo biloba',17,4.0,4.0,5,1.5,'deciduous',['shade-plan','fall-color-study'],'upright-ovoid-fan-leaves'),
      ('plane','二球悬铃木','Platanus × acerifolia (hybrid; reported local use)',20,7.0,4.8,6,2.5,'deciduous',['shade-plan','city-streettrees','plane-flora'],'broad-forked-pale-bark'),
      ('peach','碧桃','Prunus persica ornamentalcultivar; exactcultivar unknown',5.0,2.8,1.5,1.5,.9,'deciduous',['unesco-westlake'],'low-open-forked'),
      ('sweetgum','枫香','Liquidambar formosana',20,5.3,5.0,6,1.8,'deciduous',['fall-color-study','westlake-forest-history'],'upright-irregular-ovoid'),
      ('masson-pine','马尾松','Pinus massoniana',22,5.6,7.0,7,2.0,'evergreen',['westlake-forest-history'],'open-layered-umbrella-pine')]
    species=[]
    for sid,name,latin,h,r,clear,he,re,life,backing,habit in dims:
        species.append({'id':sid,'name':name,'scientificName':latin,'leafHabit':life,'form':habit,'sourceIds':backing,
            'prototypeHeightM':h,'prototypeCrownRadiusM':r,'prototypeBranchClearanceM':clear,'trunkRadiusM':.38 if h>15 else .28 if h>8 else .13,
            'dimensionsBasis':'estimated','heightErrorPlusMinusM':he,'crownRadiusErrorPlusMinusM':re,
            'dimensionMethod':'bounded procedural mature/maintained archetype selected from reportedlarge/smalltree categories andsourcecrown habit. Dimensions do not identify or measure anindividual real tree.',
            'seasonBasis':'reported botanical/scene descriptions; exactyear/weather/pruning/cultivar dates unknown',
            'latitudePositionInventory':'unknown; no species-tagged tree locations generated',
            'growthStage':'representative maintained adult, not ancient-tree replica'})
    scene={'west-lake-causeways':{'preferred':['willow','peach'],'basis':'reported traditional combination','sourceIds':['unesco-westlake'],
        'designRules':'alternate/clustered source-informed palette, preserve bank/bridge path andcamera clearance; actualtreecountsandlocationspending'},
      'urban-streets':{'preferred':['camphor','plane','ginkgo','sweetgum'],'basis':'reported local planning/research palette; authoredweightsnotfixedcensus',
        'sourceIds':['shade-plan','city-streettrees','fall-color-study'],'designRules':'follow streettiers/viewwindows/independentsides; selectedsource-certainroads mayretain documentedtheme; no randomplaneonsmallcauseway'},
      'parks-low-layer':{'preferred':['osmanthus','peach'],'basis':'reported plantingcategories, estimatedmix','sourceIds':['shade-plan','osmanthus-experts'],
        'designRules':'smallround crowns near publicgardens; flowersseason-specific; keepcafe/camera/interaction plots clear'},
      'hillside-canopy':{'preferred':['camphor','sweetgum','masson-pine'],'basis':'reported historicalWestLake hills/regionalspecies; current perhill proportionsunknown',
        'sourceIds':['westlake-forest-history','westlake-adoption'],'designRules':'mixbroadleaved/matureopenpine crowns, varied heights/terrain; notmonotonegiantbanyan/Phoenix vegetation'}}
    pending=['actualtreeinventory/speciespositionsandperstreet/pruning/banktree counts','currentbotanicalleaf/bark close visualreview andspecies-specific multifacingfieldphotos',
        'all absoluteprototype dimensions areestimated; actualindividual tree heights/DBH/crownspreadunknown',
        'current2026 seasonal phenology/pruning/cultivar differences; palette isstatic selectableassetvariant, no claimofnewseason gameplay',
        'parent Blenderexport/materialregistration/GLB budgets/manifests andinstanceplacements','GPU day/night materials/shadows andLOD popping/thininstance compatibility','clearance atroads/water/landmarks/cafe/pedestrianpaths andrealbrowser/performance']
    palette={'schemaVersion':1,'id':'hangzhou-tree-palette','cityId':'hangzhou','scope':'eight original procedural regional tree archetypes ×threeLODs, localprototype coordinates; no individualtree census/reconstruction',
        'species':species,'scenes':scene,'coordinatePolicy':{'dimensions':'realmetres untilbuild','scaleOnce':.6,'prototypeSpace':'local east/north/up, root at0','lm':'gameunittranslation andheight, not scaledagain',
            'runtime':'variation scale only; downloadedGLB height/crown metadata alreadygameunits','rootTransform':'keepexistingBlender→GLB→Babylon directionhandling'},
        'lodBudgets':{'0':{'maxTriangles':4800,'maxMaterials':5},'1':{'maxTriangles':1700,'maxMaterials':4},'2':{'maxTriangles':220,'maxMaterials':3}},
        'defaultSeason':'summer','supportedAssetSeasons':['summer','spring','autumn','winter'],'seasonDoesNotAddGameplaySystem':True,
        'materialPolicy':'proceduralsolidcrowns/bark, no alphacards/photo textures; optional parent registered matte material slots, default existingBmaterials',
        'pendingSubscopes':pending}
    ph=write('palette-spec.json',palette);write('source-list.json',{'sources':sources})
    write('evidence.json',{'schemaVersion':1,'scope':palette['scope'],'stage':'asset-evidence-ready; generic localasset family, not geographiclandmarkCLIverified',
        'sources':sources,'reported':['regional palette/scene assignments','evergreen/deciduous andseasonalcolor/flower categories','morphologicaltypes'],
        'estimated':[{'species':s['id'],'heightM':s['prototypeHeightM'],'crownRadiusM':s['prototypeCrownRadiusM'],'heightErrorPlusMinusM':s['heightErrorPlusMinusM'],'crownRadiusErrorPlusMinusM':s['crownRadiusErrorPlusMinusM'],'method':s['dimensionMethod']} for s in species],
        'measured':[],'unknown':['species-tagged currenttree points','individual surveyed dimensions','currentpercentages/census','exact2026phenology'],
        'sourceSnapshots':{str((HERE/name).relative_to(ROOT)):sha(HERE/name) for _,name,*_ in files},'paletteSpecSha256':ph,'blockers':[],
        'pendingSubscopes':pending,'notes':'finitearchetypescope permitsestimatedsizes; individualtrees/fieldaccuracy unresolved; no geographiclocation invented'})
    write('job.json',{'schemaVersion':1,'place':{'id':'hangzhou-tree-palette','kind':'local-procedural-asset-family'},'stage':'evidence-ready',
        'history':[{'stage':'planned','date':'2026-10-14','reason':'parentauthorizedlocal treearchetype research/module'},
                   {'stage':'evidence-ready','date':'2026-10-14','reason':'sourcefilesactuallyread, categories/sizesandunknownscopefrozenbeforemodule'}],
        'coordinatePolicy':palette['coordinatePolicy'],'sourceSpecSha256':ph,'ownership':{'workerFiles':['scripts/landmarks/hangzhou_tree_palette.py'],'workerDirectories':[str(HERE.relative_to(ROOT))],'sharedOwner':'root serialintegrator'},
        'budget':palette['lodBudgets'],'contract':'localasset evidence gate, notWGS84landmarktask CLI; no standalone georeferencedtreeinventories asserted'})
    write('model.json',{'sourceModule':'scripts/landmarks/hangzhou_tree_palette.py','sourceModuleSha256':None,'artifacts':[],'buildCommand':None,'stage':'module-pending','accuracyClaim':'originalproceduralarchetypes; estimateddimensions'})
    write('validation.json',{'artifactSha256':None,'evidenceSha256':sha(HERE/'evidence.json'),'checks':{k:{'status':'unknown','evidencePaths':[]} for k in ['scale','orientation','silhouette','context','collision','browser','performance','provenance']}})
    g=load_city('hangzhou')['geography']
    for sp in species:
        for lod in range(3):
            write(f'prototype-specs/{sp["id"]}-lod{lod}.json',{'id':f'hz-tree-{sp["id"]}-lod{lod}','cityId':'hangzhou','speciesId':sp['id'],'lod':lod,'season':'summer',
                'anchor':{'lon':g['originWGS84'][0],'lat':g['originWGS84'][1],'basis':'neutralcanonicaloriginforlocalassetexport, not a surveyedtree location'},
                'prototype':sp,'paletteSpecSha256':ph,'scope':palette['scope'],'baseBuildingIdsToExclude':[],'pendingSubscopes':pending,
                'budget':palette['lodBudgets'][str(lod)]})
    print(json.dumps({'species':len(species),'prototypeSpecs':24,'paletteSpecSha256':ph,'geographicTreeInventoryGenerated':False}))

if __name__=='__main__':main()
