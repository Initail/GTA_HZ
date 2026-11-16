"""Bounded annex research spec; deliberately no runnable world geometry."""
import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,j):(HERE/n).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')

def main():
    ref=HERE/'references';sources=json.loads((ref/'fetches-all.json').read_text())['sources']
    for name in ['sinomach-source.json','gov-project-source-fetches.json','gov-completion-source-fetches.json']:
        j=json.loads((ref/name).read_text());sources += j.get('sources',[j])
    for s in json.loads((ref/'planning-lead-images.json').read_text())['sources']:
        if s['id'].startswith('gov-header'):continue
        s=dict(s,publisher='小易看财经/杭州建设规划转载',authority='reproducedplanningimage;originalgovsheetnotrecovered',sourceDate='2024-04-26' if s['id'].startswith('phase1') else '2025-07-08')
        sources.append(s)
    original=json.loads((HERE.parent/'sources.json').read_text())['sources']
    for s in original:
        if s['id'] in ['aedas-cainiao','cscec-cainiao','cainiao-contact']:sources.append(dict(s,localPath=s['path']))
    for s in json.loads((HERE.parent/'cainiao-round2/references/manifest.json').read_text())['sources']:
        if s['id'] in ['aedas-photo-Headquarters','aedas-photo-3','aedas-gooood-photo-001']:sources.append(dict(s,localPath=s['path']))
    for s in sources:
        if s.get('localPath'):
            path=ROOT/s['localPath'];assert sha(path)==s['sha256'],s['id']
            s['localPath']=str(path.relative_to(ROOT))
    raw=json.loads((HERE/'raw-osm-objects.json').read_text())
    sources.append({'id':'geofabrik-fixed-raw','url':raw['source']['sourceUrl'],'publisher':'Geofabrik/OpenStreetMapcontributors','sourceDate':raw['source']['osmReplicationTimestamp'],'accessedAt':'2026-10-14','license':'ODbL-1.0','localPath':'data/raw/hangzhou/zhejiang-261011.osm.pbf','sha256':raw['source']['sha256'],'use':'Allrawnode/way/relation tags andcorners inspected; no missedannexbuildingparts'})
    prior=json.loads((HERE.parent/'alibaba-a-round3/cainiao-source-audit.json').read_text());parcels=prior['parcels']
    # Stable positional research aliases are not official building numbers.
    north=[('N-SW','west-south-tower',[82,214,156,310]),('N-WN','west-north-tower',[196,135,311,216]),
        ('N-CS','central-south-tower',[363,229,475,309]),('N-CN','central-north-tower',[548,134,656,216]),
        ('N-ES','east-south-tower',[731,231,827,309]),('N-EN','east-north-tower',[862,150,1008,229]),
        ('N-NW-low','northwest-low-ancillary',[88,132,181,202])]
    objects=[]
    for sid,role,bbox in north:
        objects.append({'id':sid,'zone':'northmappedparcel/phase1reportedcontext','researchAliasOnly':True,'physicalCurrentOfficialNumber':None,
            'sourceParcelId':'way/1293416973','role':role,'reference':'phase1-usechange-repost-5','imageSizePixels':[1080,379],
            'roughImageBodyBBoxPixels':bbox,'imageBoundsBasis':'estimatedmanualreference-index,notfootprintpolygon','imageBoundsErrorPlusMinusPixels':6,
            'rawBuildingSourceId':None,'footprintWGS84':None,'heightM':None,'currentEntryWGS84':None,
            'bodyFeatures':{'plan':'Roundedcornersandattachedlowwing/platform shown; outline mustbe digitizedfromoriginalsheet','facade':'Dense horizontal pale bands, darkglass, roundedcorners, roofgarden/centralequipment evidentfromrealAedas overview','allSides':'unknown'},
            'sourceIds':['sinomach-phase1-2020','phase1-usechange-repost','phase1-usechange-repost-5','phase1-usechange-repost-6','phase1-usechange-repost-7','aedas-photo-Headquarters'],
            'status':'identifiedreferencebody-location;worldfootprint/officialnumbercrosswalkblocked'})
    # East diagram has10 principal planned bodies; aliases use diagram order.
    east=[('E-NW-low',[201,150,270,196]),('E-NM1-low',[291,131,375,187]),('E-NM2-low',[404,128,471,191]),
        ('E-WS-low',[223,219,309,289]),('E-SM1-low',[348,263,428,325]),('E-SM2-low',[460,283,526,338]),
        ('E-CN-tower',[503,146,594,227]),('E-CS-tower',[576,243,680,327]),('E-EN-tower',[805,139,896,234]),('E-ES-tower',[711,247,817,329])]
    for sid,bbox in east:
        objects.append({'id':sid,'zone':'eastmappedparcel/phase2reportedcontext','researchAliasOnly':True,'physicalCurrentOfficialNumber':None,
            'sourceParcelId':'way/1293548829','role':sid.split('-')[-1],'reference':'phase2-usechange-repost-6','imageSizePixels':[1080,449],
            'roughImageBodyBBoxPixels':bbox,'imageBoundsBasis':'estimatedmanualreference-index,notfootprintpolygon','imageBoundsErrorPlusMinusPixels':7,
            'rawBuildingSourceId':None,'footprintWGS84':None,'heightM':None,'currentEntryWGS84':None,
            'bodyFeatures':{'plan':'Sixlower+fourlargerbodyreferences;not10identicaltowers; continuouswavepublicplatform andplazas shown','facade':'Roundedcorner horizontalskins androoftopgreen/mechanicalboxfamily visibleinAedas actualcampusphoto','heightHierarchy':'Sourceplan/sourceaerial showsmix oflowandhigherobjects; perbodyroof/levelsmustbe reviewed'},
            'sourceIds':['zjol-phase2-2019','phase2-usechange-repost','phase2-usechange-repost-6','phase2-usechange-repost-7','aedas-photo-Headquarters'],
            'status':'historical10bodyplanreferences;asbuiltcrosswalk/worldfootprintsblocked'})
    objects.append({'id':'HQ-east-annex','researchAliasOnly':True,'zone':'HQparcel-easternside','sourceParcelId':'way/1228913717',
        'physicalCurrentOfficialNumber':None,'rawBuildingSourceId':None,'footprintWGS84':None,'currentEntryWGS84':None,
        'role':'visitor/auditoriumcomplexrelationshipunresolved','bodyFeatures':{'visible':'Lowrectangular/roundededge ancillarybodyeastofHQ; broadroofincludesgold-tonedsegmentandlightsegment,glassfacade andlinktoHQ','unknown':'Reportedauditorium4F doesnotprove allvisiblevisitorparts fourfloors/oneindependentbuilding'},
        'reportedProgram':{'auditoriumCount':1,'auditoriumFloors':4,'basis':'reported','sourceIds':['cscec-cainiao']},
        'heightEstimateForAuditoriumOnly':{'valueM':18,'errorPlusMinusM':4,'basis':'estimated','method':'Reported4F ×3.5–4.5m typicalpublicbuildingpitch +0–2m roof parapet; broadtypologicalestimate, not photoheightsurvey. Other visitorparts maydiffer; no modelmade.'},
        'sourceIds':['aedas-cainiao','cscec-cainiao','aedas-photo-Headquarters','aedas-gooood-photo-001'],'status':'realannexvisible;footprint/visitor-auditoriumsubdivisionblocked'})
    blockers=[{'id':'rawcoverage','reason':'FullfixedPBF9building/partwayrecords areHQplusmetroonly;all9exactlyinextract. No annexe/towerpart hiddenbytagfilter. Cannot useparcelredline asindividualbuildingfootprint.'},
        {'id':'originalplans-and-coordinateframe','reason':'2024/2025reproducednoticeplans haveindividualoutlines/localXYgrid, but originalgovsheet/completeannotations/coordinateCRSnot recovered. X≈82300/Y≈60600 cannotbe blindlyconverted toWGS84.'},
        {'id':'asbuilt-body-crosswalk','reason':'Sixmain+aux vs7count andhistorical10plan figures use differentphysical/perioddefinitions;percurrentA/Bnumbers/floorplans/rooftops remainunregistered. Six/7/10 notautomaticallysameasphotoassetnodecount.'},
        {'id':'entrance-platform-andlevels','reason':'Localdrawinggatesandwaveplatforms visiblebutactualWGS84gatepoints,deckbase/roadcrossing clearance and currentpublicaccessunknown. No centerpointgoal or guessedbridge connections.'}]
    spec={'id':'cainiao-annex','cityId':'hangzhou','status':'evidence-spec-only;coverage-blocked','scope':'Localreferencebody list for6northproductiontowers+ancillaryreference,10eastplanbodies,andHQeastannex; notwholecampus modelcompletion',
        'sourcePbfSha256':raw['source']['sha256'],'sourceRawAuditPath':str((HERE/'raw-osm-audit.json').relative_to(ROOT)),
        'sourceRawAuditSha256':sha(HERE/'raw-osm-audit.json'),'coordinatePolicy':{'sourceGeometry':'EPSG:4326fixedOSMparcels;individualplanXY CRSunknown','worldFootprintRegistration':'blocked,nonegenerated','physicalMetreScaleOnce':.6,'lmY':'already-scaledgameunits','direction':'east/north/up→existingGLB/Babylon policy'},
        'mappedParcels':parcels,'objects':objects,'buildingCountLedger':[
            {'sourceId':'sinomach-phase1-2020','basis':'reported','epoch':'2020planned','northPhase1PrimaryCount':6,'ancillaryCount':None},
            {'sourceId':'phase1-usechange-repost','basis':'reported-fromnotice-republication','epoch':'2024','northPhase1BuildingsIncludingPodiumCount':7,'originalGovernmentDocumentVerified':False},
            {'sourceId':'zjol-phase2-2019','basis':'reported','epoch':'2019planned','eastPhase2PrimaryCount':10,'asbuiltCountVerified':False},
            {'sourceId':'cscec-cainiao','basis':'reported','epoch':'2023deliveredHQcontract','HQMainCount':1,'HQMainFloors':5,'auditoriumCount':1,'auditoriumFloors':4}],
        'reportedReproducedDiagramMetrics':{'northMaxBuildingHeightM':59.95,'northMaxFloorMetric':13,'basis':'reported-fromreproducedplanlabel,notfieldmeasured','perBuildingAssignment':'unknown','localXYDatum':'unknown','sourceId':'phase1-usechange-repost-8'},
        'facadeAndRoofScheme':{'sourceBasedFeatures':['varyinglow/highroundedrectbodies','horizontalpale floorfins/darkglazing','greenroofs+centralequipment','wave/curvedupperpublicplatform withvoids/plazas','HQannexbroadgold/lightroofandglass'],'perBodyFacadePhotoRegistration':'pending','night':'actualfixture/schedule/photometric proofpending','noSourcePhotoTextures':True},
        'baseBuildingIdsToExclude':[],'moduleCreated':False,'budgetProvisional':{'maxTriangles':25000,'maxMaterials':12,'maxBytes':8388608},'blockers':blockers}
    save('evidence-spec.json',spec);save('object-register.json',{'scope':spec['scope'],'objects':objects,'doNotUseReferenceImageBoxesAsSurveyedFootprints':True})
    save('source-list.json',{'places':[{'id':'cainiao-annex','name':'菜鸟总部附属及产业楼群足印调查（当前覆盖阻塞）','kind':'building-group','location':{'center':[119.96197745,30.2654788]},'sources':sources,'modeling':{'status':'blocked-before-model','blockers':blockers}}]})
    print(json.dumps({'sourceRecords':len(sources),'referenceBodyObjects':len(objects),'moduleCreated':False,'blockers':len(blockers)},ensure_ascii=False))
if __name__=='__main__':main()
