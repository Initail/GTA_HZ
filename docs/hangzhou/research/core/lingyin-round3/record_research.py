"""Record bounded source claims/task inputs; does not modify prior packages."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
BASE=ROOT/'docs/hangzhou/research/core/lingyin-round2'


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    spec=json.loads((OUT/'spec.json').read_text())
    previous=json.loads((BASE/'source-claims.json').read_text())
    sources=previous['sources']+[
      {'id':'official-axis-2011','url':'https://www.lingyinsi.org/detail_22_673.html',
       'publisher':'杭州灵隐寺（运营方官网）','accessedAt':'2026-10-14','sourceDate':'2011-10-09','status':'available',
       'license':'Reference-only operator prose/photos; no photograph release permission obtained',
       'title':'灵隐今朝添龙象 冷泉回波助狮吼'},
      {'id':'heritage-layout-paper','url':'https://www.wochmoc.org.cn/upload/file/202004/1588058384711036046.pdf',
       'publisher':'赵云、黄雯兰（文内署名中国文化遗产研究院）；公开PDF托管于wochmoc.org.cn',
       'accessedAt':'2026-10-14','sourceDate':None,'status':'available',
       'title':'试论唐五代至近现代灵隐寺建筑布局的演变',
       'sha256':digest(Path('<TEMP>/hz-lingyin-layout-paper.pdf')),'bytes':1505137,
       'sourceDateLimit':'PDF metadata created2020-03-08; hosting path202004. Publication year not established, neither treated as survey date.',
       'license':'Copyright retained by publisher/authors; read/render temporary cache only, PDF/page pixels not bundled',
       'review':'Actual PDF page4(printpage60) viewed; Fig5 is expressly redrawn from temple incense-route diagram, without scale/georeference/height datum.'},
      {'id':'source-han-serif','url':'https://github.com/adobe-fonts/source-han-serif',
       'publisher':'Adobe','accessedAt':'2026-10-14','sourceDate':None,'status':'available',
       'license':'SIL Open Font License1.1; original font copyright2017–2022Adobe, Reserved Font Name Source',
       'fontUrl':spec['glyphSource']['url'],'fontSha256':spec['glyphSource']['sha256'],
       'licenseUrl':spec['glyphSource']['licenseUrl'],'localLicensePath':str((OUT/'SourceHanSerif-OFL.txt').relative_to(ROOT)),
       'use':'Derived glyph foreground rectangle geometry for wording, not a font or photograph texture distribution'}]
    claims=[
      {'kind':'identity/axis','basis':'reported','sourceIds':['official-axis-2011','temple-2014','heritage-layout-paper'],
       'value':['天王殿','大雄宝殿','药师殿','直指堂（法堂）/藏经楼','华严殿'],
       'method':'Temple operator description and modern Fig5 confirm order. Frozen fixed-OSM five polygons remain the actual spatial evidence.',
       'uncertainty':'Historical publications and uncalibrated modern diagram; not current2026 cadastral/entrance survey'},
      {'kind':'boundary','basis':'unknown','sourceIds':['heritage-layout-paper','intro-official'],
       'polygonWGS84':None,'method':'Read Fig5 and prior official overview; schematic enclosure only, no source control points or lawful parcel ring.',
       'blocker':'Do not convert an illustration outline, whole scenic/nature-reserve polygon or total reported acreage into a temple boundary.'},
      {'kind':'local-terraces','basis':'estimated','sourceIds':['kings-official','grand-official','medicine-official','dharma-official','huayan-official','axis-photo-2020','hall-photo-2020'],
       'value':spec['terraces'],
       'uncertainty':'Per-hall broad modelling allowances in spec. No floor datum, measured stair counts or current platform footprints obtained.'},
      {'kind':'historic-dimensions','basis':'reported-historic','sourceIds':['heritage-layout-paper'],
       'use':'not-used-for-current-halls','reason':'Table on paper page4 is explicitly Qing-era building dimensions; it cannot replace current operator33.6m GrandHall or fixed OSM shell widths.'},
      {'kind':'plaques','basis':'reported-wording/estimated-placement','sourceIds':['kings-official','grand-official','medicine-official','dharma-official','axis-photo-2020','hall-photo-2020'],
       'value':spec['inscriptions'],'method':'Actual reference photos checked; traditional text placed in right-to-left order using independently rasterized open font geometry.',
       'uncertainty':'No claim of historic calligraphic facsimile, exact size/color/strokes. GrandHall third/top old blank plaque and Huayan upper inscription are unconfirmed and remain blank.'},
      {'kind':'ridge','basis':'estimated','sourceIds':['roof-photo-2021'],
       'value':spec['detailEstimates']['ridgeEnds'],'method':'Generic pale ceramic upward curl silhouette only; reference close-up hall assignment unknown.',
       'uncertainty':'No per-hall dragon/carving replica, surveyed counts or roof sculpting fidelity claim'},
      {'kind':'ground','basis':'unknown','sourceIds':['osm-geofabrik'],
       'value':{'hallBaseYGame':spec['hallBaseYGame'],'absoluteThresholdYGame':None,'actualStepCount':None},
       'method':'Read-only terrain-v3 source context in context-check.json. Absolute game bases are required external inputs; no automatic terrain sample chosen.',
       'uncertainty':'EGM2008 DSM/filter is not surveyed floor and cannot mix directly with YellowSea/other height datums.'}]
    blockers=[
      {'id':'lingyin-floor-datum','status':'pending','scope':'real site joining','reason':'Five actual plinth/threshold absolute heights and datum unmeasured; module accepts explicit external game-Y only.'},
      {'id':'lingyin-boundary','status':'pending','scope':'whole monastery','reason':'No cadastral/current georeferenced outer ring; schematic maps do not establish it.'},
      {'id':'lingyin-stair-run','status':'pending','scope':'continuous axial routes','reason':'True platform extent, step count/rise/width and connection nodes missing. Nearby OSM steps are not automatically axial hall stairs.'},
      {'id':'lingyin-entry','status':'pending','scope':'safe accessible arrival','reason':'Original hall bodies/doors are closed shells. Terrain cuts, obstacle-free arrival and accessible paths need serial runtime evidence.'},
      {'id':'lingyin-decoration','status':'pending','scope':'full exterior visual accuracy','reason':'Representative open-font lettering and ridge shapes; true carving/calligraphy/paint/back facades/current materials not verified.'}]
    write('source-claims.json',{'schemaVersion':1,'scope':spec['scope'],'sources':sources,'claims':claims,'blockers':blockers,
      'photosBundled':False,'copyrightedPdfBundled':False,'surveyedFloorClaim':False,
      'dateLimit':'Published2011–2021 reference photos may differ from current appearance; no2026 site survey.'})
    oldphotos=json.loads((BASE/'photo-review.json').read_text())
    chosen={'kings','grand','medicine','dharma-wide','huayan-wide','roof-detail-correct'}
    photographs=[{**p,'reviewedAt':'2026-10-14','newReview':'actually viewed again in temporary cache; wording/terrace/roof detail only'} for p in oldphotos['photos'] if p['id'] in chosen]
    write('photo-review.json',{'schemaVersion':1,'photographsActuallyReViewed':photographs,
      'heritagePlan':{'sourceId':'heritage-layout-paper','pdfPageZeroIndex':3,'printedPage':60,
        'reviewMethod':'Poppler render then actual view_image','observation':'Fig5 modern diagram, axiscourtyards/wings; no scale/WGS84/legal boundary/levels. Qing-era table not used for current dimensions.',
        'bundled':False},
      'fontGlyphSheet':{'path':'font-glyph-cpu-sheet.png','actualViewedAt':'2026-10-14','purpose':'26 traditional glyph coverage check; original open-font output'},
      'limitations':'Photos reference only; no release textures or author/owner copyright permission fabricated.'})
    evidence=json.loads((BASE/'evidence.json').read_text())
    evidence.update({'scope':spec['scope'],'sources':sources,'pendingSubscopes':spec['pendingSubscopes'],
      'sourceSnapshots':{str(p.relative_to(ROOT)):digest(p) for p in [BASE/'spec.json',BASE/'source-claims.json',BASE/'photo-review.json',OUT/'spec.json',OUT/'source-claims.json',OUT/'context-check.json']},
      'photoReview':str((OUT/'photo-review.json').relative_to(ROOT)),
      'stageLimit':'evidence-ready for explicit game-Y adapter and limited estimated details only; actual monastery ground/route subscopes pending. No GLB or formal/current8checks.',
      'fullSiteBlockers':blockers})
    evidence['observations'].extend([
      {'kind':'site-adapter','basis':'estimated','sourceIds':['osm-geofabrik','heritage-layout-paper','official-axis-2011'],
       'value':'Five absolute game-Y bases supplied externally; no automatic DSM/floor inference; original shells retained; local terrace/stairs openly estimated.',
       'unit':None,'uncertainty':'Exactfloor/step/whole-boundary/continuousroute remains pending; explicit caller input does not certify real elevation.'},
      {'kind':'detail','basis':'estimated','sourceIds':['axis-photo-2020','hall-photo-2020','roof-photo-2021','source-han-serif'],
       'value':'Reference-transcribed traditional plaques, sparse pale stone balustrades/paving and representative curling roof ridge ends.',
       'unit':None,'uncertainty':'No photo texture/traced calligraphy, scanned relief or final material/visual claim.'}])
    write('evidence.json',evidence)
    write('task-catalog.json',{'places':[{'id':'lingyin-temple','name':'灵隐寺五殿独立基高与有限场地细部候选','kind':'building-group',
      'location':{'center':[spec['anchor']['lon'],spec['anchor']['lat']]},'sources':sources,'modeling':{'blockers':[]},'scope':spec['scope']}]})
    write('attempts.json',{'schemaVersion':1,'actualAttempts':[
      {'action':'official references and actual PDF/photo review','result':'completed-limited','notes':'Six official photo views re-reviewed, research Fig5 viewed. No measuredfloor/cadastralboundary/steps inferred.'},
      {'action':'official restoration detail_46_778 text','result':'unavailable','notes':'www.lingyinsi.com timeout; org variant not accessible. Not used as a grounded source or height.'},
      {'action':'Adobe OFL font initial transfer','result':'partial-failed','notes':'35s timeout16,500,261/24,542,148bytes; initial Pillow partialfont load failed hmtx. Partialfile not used.'},
      {'action':'Adobe font bounded resumed transfer','result':'completed','sha256':spec['glyphSource']['sha256'],'bytes':24542148,'notes':'Complete hash and FreeType font load checked before glyph generation.'},
      {'action':'first CPU triangle budget','result':'failed','triangles':31858,'ceiling':30000,'notes':'Budget kept30000; removed fully hidden contact faces and replaced fragmented ridge blocks with short closed curved strips.'},
      {'action':'first fixed OSM vertex comparison','result':'failed-and-corrected','notes':'Initial check assumedPolygon nesting. Actualprocessedfeatures are singlepartMultiPolygon; corrected ring extraction with strictpart/hole assertions, exact all5vertexsets then matched.'},
      {'action':'CPU geometry/API validation','result':'passed-host-contract-only','triangles':29784,'materials':6,'collisionPolygons':348,
       'notes':'Shellstream equality, independentgameY shifts, fixedcentroids/single.60, valid bounds, floor/step surfaces and explicitmissinginput rejection.'},
      {'action':'CPU drafts','result':'generated-and-actually-viewed','views':['cpu-top.png','cpu-street.png','cpu-distant.png','cpu-grand-plaque-close.png'],'notes':'Original CPU previews using openly synthetic Y, not game/terrain/photo acceptance.'},
      {'action':'Blender/browser/shared assets/config','result':'not-run','reason':'Parent serially owns integration; only newsite module and round3 folder written'}]})
    preview=json.loads((OUT/'cpu-preview-manifest.json').read_text())
    for v in preview['views']:
        v['reviewStatus']='actually viewed by landmark_evidence; draft-only; formal visual acceptance unknown'
        v['reviewedAt']='2026-10-14'
    write('cpu-preview-manifest.json',preview)
    print(json.dumps({'sources':len(sources),'actualPhotoViews':len(photographs),'fullSitePendingBlockers':len(blockers),'scope':'newround3 only'},ensure_ascii=False))


if __name__=='__main__':main()
