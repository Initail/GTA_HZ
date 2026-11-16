"""Record photographs actually viewed; cache pixels never enter the release."""
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
    n='https://www.nbbj.cn/wp-content/uploads/2022/'
    refs=[
      ('nbbj17','nbbj',n+'07/ShaoFeng-00017_screenview.jpg','jpg',
       'ground, looking into a broad shell/bowl opening; exact geographic azimuth unknown',
       'Large petal opening exposes red seating and white diagonal pipe trusses; behind-shell glazed volumes and stairs; not proof of a surveyed gate level.',None),
      ('nbbj08','nbbj',n+'07/ShaoFeng-00008_screenview-2000x1333.jpg','jpg',
       'night ground/bridge oblique frontage; geographic azimuth uncalibrated',
       'Broad pale petals, narrow translucent interleaves, visible curved seams and violet wash; raised walking bridge cannot be represented as flat ground.',None),
      ('nbbj05','nbbj',n+'07/ShaoFeng-00005_screenview.jpg','jpg',
       'day distant side from park/bridge foreground; geographic azimuth unknown',
       'Overall pale petal shell, raised stadium terrace and low riverpark context; no calibrated height ruler.',None),
      ('nbbj77','nbbj',n+'08/100526_00_Hangzhou_N77_screenview.jpg','jpg',
       'actual close street façade with visitors and entranceD banner; azimuth unknown',
       'Petals taper toward their ground tips, bulge above, then curl over; thin panel lines and narrow louver/translucent gaps with triangular trusses.',None),
      ('nbbj69','nbbj',n+'07/100526_00_Hangzhou_N69_screenview.jpg','jpg',
       'same far park/bridge composition asnbbj05 at another size/crop',
       'Duplicate viewpoint, not counted as an additional direction.','nbbj05'),
      ('nbbj82','nbbj',n+'07/100526_00_Hangzhou_N82_screenview.jpg','jpg',
       'interior circulation/underside detail, not an exterior elevation',
       'White crossed trusses and louver underside over stairs/railings support a thin open shell rather than a solid outer wall.',None),
      ('nbbj22','nbbj',n+'07/100526_00_Hangzhou_N22_screenview.jpg','jpg',
       'actual bowl interior from lower seating/field towards the canopy',
       'Three seating tiers; red/blue seat patches; large opening, curved roof-edge beam, diagonal steel bracing; no individual seat inventory measured.',None),
      ('site-plan','nbbj',n+'07/HANGZHOU_SITE-PLAN-01_screenview.jpg','jpg',
       'architect site-plan illustration, not a current georeferenced photograph',
       'Main stadium and tennis center are independent objects, park/plazas/bridges surround both, representative track/field in bowl; page orientation not used as WGS84 direction.',None),
      ('operator-aerial','operator','https://tms.bjatzxjq.com/uploads/dalianhua/054cb9076657bfa0571a7a91533e88ce.jpg','jpg',
       'actual aerial dusk oblique from south side towards the river/north-bank skyline; exact camera coordinate/azimuth unknown',
       'Entire annular petal roof and open center visible; broad pale lobes with narrow dark interleaves. Field has a temporary concert setup, not a permanent building. Raised platforms and petal-tip lighting visible.',None),
      ('operator-banner','operator','https://tms.bjatzxjq.com/uploads/dalianhua/26475e747f74024f02f8f58f6f0cb1b1.png?width=1920','png',
       'same dusk aerial asoperator-aerial, cropped banner',
       'Duplicate aerial view, not a second direction.','operator-aerial')]
    review=[]
    for ident,source,url,ext,view,obs,duplicate in refs:
        p=Path('<TEMP>/hz-big-lotus-'+ident+'.'+ext);assert p.is_file()
        review.append({'id':ident,'sourceId':source,'url':url,'sha256':digest(p),
          'downloadBytes':p.stat().st_size,'reviewedAt':'2026-10-14','reviewedBy':'landmark_evidence',
          'reviewMethod':'actual view_image of temporary source cache','view':view,
          'captureDate':None,'cameraCalibration':None,'observations':obs,'duplicateOf':duplicate,
          'license':'unknown; source and credited photographer retain rights',
          'bundled':False,'releaseTexture':False})
    write(OUT/'photo-review.json',{'schemaVersion':1,'references':review,
      'directions':'At least actual street exterior, riverpark far-side and aerial exterior views; azimuth uncalibrated. Interior/plan and duplicates are not counted as separate façade directions.',
      'limitations':['No2026 site survey is claimed.','Source URL upload date is not a photograph capture date.',
        'No official image becomes a texture, tracing atlas or packaged release file.',
        'NBBJ site drawing does not define modern WGS84 geometry; OSM is retained for positioning.']})
    evidence=json.loads((OUT/'evidence.json').read_text())
    evidence['photoReview']=PREFIX+'/photo-review.json'
    evidence['sourceSnapshots'][PREFIX+'/photo-review.json']=digest(OUT/'photo-review.json')
    write(OUT/'evidence.json',evidence)
    jobdir=OUT/'task-bundles/big-lotus';write(jobdir/'evidence.json',evidence)
    job=json.loads((jobdir/'job.json').read_text())
    job['ownership']['workerFiles']=['scripts/landmarks/big_lotus.py']
    job['ownership']['workerDirectories']=[PREFIX]
    job['budget'].update({'maxTriangles':28000,'maxMaterials':10})
    job['budget']['reason']='Main integrator authorized a <30k candidate ceiling;55 independent curved petals and an open three-tier bowl are larger than a single tower. Provisional28000 limit fixed before CPU build; actual export/runtime still pending.'
    write(jobdir/'job.json',job)
    model=json.loads((jobdir/'model.json').read_text())
    spec=json.loads((OUT/'spec.json').read_text())
    model.update({'sourceModule':'scripts/landmarks/big_lotus.py',
      'artifactPath':'artifacts/cities/hangzhou/landmarks/big-lotus-v1/big-lotus.glb',
      'artifactMeshPrefix':'detail_big-lotus_','sourceSpec':PREFIX+'/spec.json',
      'sourceSpecSha256':digest(OUT/'spec.json'),'buildCommand':None,
      'estimatedParameters':spec['estimates'],
      'notes':'No Blender export executed by this worker. Main integration owns actual GLB, official material matching, platform/arrival/night and all runtime checks.'})
    module=ROOT/'scripts/landmarks/big_lotus.py'
    if module.is_file():model['sourceModuleSha256']=digest(module)
    write(jobdir/'model.json',model)
    prompt=jobdir/'prompt.md';prompt.write_text(prompt.read_text().replace('scripts/landmarks/big-lotus.py','scripts/landmarks/big_lotus.py'))
    print(json.dumps({'actualReferencesViewed':len(review),'duplicateReferences':2,
      'imagesBundled':False,'provisionalTriangleBudget':28000},ensure_ascii=False))


if __name__=='__main__':main()
