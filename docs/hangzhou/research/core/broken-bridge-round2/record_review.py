"""Provenance metadata for actually reviewed public photographs and PDF pages."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PREFIX=str(OUT.relative_to(ROOT))


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def main():
    refs=[
      ('government-2018','government-2018','https://www.ehangzhou.gov.cn/att/20180612/1528770914755017832.jpg',
       '<TEMP>/hz-broken-bridge-government-2018.jpg','near NE bank, oblique along SW direction, estimated from the shoreline context',
       'Night snow shows long gentle asphalt approaches, stone sides and rails; bridge is intact. Arch not clearly visible in this angle; no span measurement.'),
      ('government-rain2020','government-rain2020','https://www.ehangzhou.gov.cn/att/20200605/1591348034371043436.jpg',
       '<TEMP>/hz-broken-bridge-government-rain2020.jpg','lake-side distant view towards north shore/bridge; rough NW view, not calibrated',
       'Single small opening amid long stone approaches; gradual deck hump; Baochu Pagoda/hill backdrop. Image low resolution and boats partly obscure the opening.'),
      ('government-night2023','government-night2023','https://www.ehangzhou.gov.cn/att/20230907/1694076372717098140.jpg',
       '<TEMP>/hz-broken-bridge-government-night2023.jpg','near NE entrance looking along bridge, uncalibrated',
       'Street view confirms a continuous rising walkway and existing lamps; crowd/foreground obscures precise rail/arch structure. Photo caption dates scene to Aug12,2023.')]
    photos=[]
    for ident,source,url,path,view,observation in refs:
        p=Path(path);assert p.is_file()
        photos.append({'id':ident,'sourceId':source,'url':url,'sha256':digest(p),
          'downloadBytes':p.stat().st_size,'reviewedAt':'2026-10-13','reviewedBy':'landmark_evidence',
          'reviewMethod':'actual view_image of temporary source cache','view':view,'cameraAzimuth':'unknown; no EXIF/calibration',
          'observations':observation,'license':'unknown; source/credited author retains copyright',
          'bundled':False,'releaseTexture':False})
    pdf=Path('<TEMP>/hz-westlake-unesco-nomination.pdf')
    assert digest(pdf)=='5a82da9397cc7eafae35ffff8060c45c0751f6da2d5c8b40ac38ce08ad32c442'
    pages=[]
    for actual,printed,path,use in [
      (100,105,'<TEMP>/hz-westlake-page-0100.png','reported dimensions, single semicircular stone arch and asphalt slopes'),
      (107,112,'<TEMP>/hz-westlake-plan-0107.png','figure2a-59 plan: long narrow approach corridor, north arrow and pavilion cluster'),
      (108,113,'<TEMP>/hz-westlake-plan-0108.png','figure2a-61 elevation: small central arch, long gradual slopes and ruler'),
      (108,113,'<TEMP>/hz-westlake-elevation-0108.png','higher-resolution recheck of the same elevation, not an independent survey')]:
        p=Path(path);assert p.is_file()
        pages.append({'sourceId':'unesco-nomination','pdfPageOneBased':actual,'printedPage':printed,
          'renderSha256':digest(p),'reviewMethod':'pdftoppm page rendering + actual view_image',
          'reviewedBy':'landmark_evidence','reviewedAt':'2026-10-14' if actual==100 else '2026-10-13',
          'use':use,'bundled':False})
        if actual==100:
            pages[-1].update({'readAt':'2026-10-13','notes':'Text read/rendered on13; visual image view completed on14.'})
    review={'schemaVersion':1,'photos':photos,'pdfReview':{'url':'https://whc.unesco.org/uploads/nominations/1334.pdf',
      'sha256':digest(pdf),'bytes':pdf.stat().st_size,'pages':pages,
      'interpretation':'same original dossier actually downloaded/read/rendered; no substitute schematic invented',
      'limitations':'Dossier2011 metadata and undated survey basis; not2026 field evidence. Images/PDF retained only as temporary reference, not bundled.'}}
    write(OUT/'photo-review.json',review)
    evidence=json.loads((OUT/'evidence.json').read_text());evidence['photoReview']=PREFIX+'/photo-review.json'
    evidence['sourceSnapshots'][PREFIX+'/photo-review.json']=digest(OUT/'photo-review.json')
    write(OUT/'evidence.json',evidence)
    jobdir=OUT/'task-bundles/broken-bridge';write(jobdir/'evidence.json',evidence)
    spec=json.loads((OUT/'spec.json').read_text());model=json.loads((jobdir/'model.json').read_text())
    model.update({'artifactPath':'artifacts/cities/hangzhou/landmarks/broken-bridge-v1/broken-bridge.glb',
      'sourceModule':'scripts/landmarks/broken_bridge.py','sourceModuleSha256':digest(ROOT/'scripts/landmarks/broken_bridge.py'),
      'artifactMeshPrefix':'detail_broken-bridge_','sourceSpec':PREFIX+'/spec.json','sourceSpecSha256':digest(OUT/'spec.json'),
      'estimatedParameters':spec['estimates'],
      'buildCommand':'/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python scripts/build_hangzhou_landmark_candidate.py -- --job '+PREFIX+'/task-bundles/broken-bridge/job.json --spec '+PREFIX+'/spec.json --module scripts/landmarks/broken_bridge.py --output artifacts/cities/hangzhou/landmarks/broken-bridge-v1',
      'notes':'Command supplied, not executed by this worker. Main integration must bind water/ground, deck height and pedestrian arrivals before acceptance.'})
    write(jobdir/'model.json',model)
    prompt=jobdir/'prompt.md';prompt.write_text(prompt.read_text().replace('scripts/landmarks/broken-bridge.py','scripts/landmarks/broken_bridge.py'))
    write(OUT/'attempts.json',{'actualAttempts':[
      {'action':'initial PDF text extraction','result':'failed','reason':'pdftotext absent from shell PATH; direct bundled Poppler path used successfully'},
      {'action':'pypdf extraction','result':'failed','reason':'project venv lacks pypdf; bundled native Poppler used, no dependencies changed'},
      {'action':'2020 reference page bare ehangzhou domain','result':'failed','reason':'expired TLS certificate; valid www domain used, TLS verification not disabled'},
      {'action':'source evidence-ready check','result':'passed','scope':'single arch and sloping approach candidate only'},
      {'action':'first CPU check','result':'failed','triangles':13806,'reason':'above unchanged12000 provisional budget'},
      {'action':'second CPU check','result':'passed','triangles':7226,'change':'masonry joint marks use outward vertical faces rather than six-face prisms; arch/deck/rail checks retained'},
      {'action':'Blender/browser','result':'not-run','reason':'serial main integration owns heavy/export/browser work'}]})
    print(json.dumps({'photosActuallyReviewed':len(photos),'pdfPagesActuallyReviewed':[100,107,108],
                      'imagesOrPdfBundled':False},ensure_ascii=False))


if __name__=='__main__':main()
