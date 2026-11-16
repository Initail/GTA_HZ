"""Create the independent site spec from frozen halls and an OFL font.

Run with the bundled Pillow Python, passing the verified original font cache.
No bpy, scene changes, reference-photo pixels, shared assets or configuration.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BASE_SPEC = ROOT/'docs/hangzhou/research/core/lingyin-round2/spec.json'
FONT_SHA = '659c9606d8fda03372247b99ec5e5bbc5a034e06a70d80fb00546772c582d3e5'


def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def rectangles(image):
    """Merge identical horizontal runs into nonoverlapping vertical rectangles."""
    active, result = {}, []
    for y in range(image.height):
        runs, x = [], 0
        while x < image.width:
            if image.getpixel((x, y)) <= 140:
                x += 1
                continue
            start = x
            while x < image.width and image.getpixel((x, y)) > 140:
                x += 1
            runs.append((start, x))
        next_active = {}
        for run in runs:
            next_active[run] = active.pop(run, y)
        for (a, b), start_y in active.items():
            result.append([a/image.width, start_y/image.height, b/image.width, y/image.height])
        active = next_active
    for (a, b), start_y in active.items():
        result.append([a/image.width, start_y/image.height, b/image.width, 1.0])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', type=Path, required=True)
    parser.add_argument('--font-license', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.font.read_bytes()).hexdigest() != FONT_SHA:
        raise ValueError('Complete original Adobe font hash required, not a partial download')
    if hashlib.sha256(BASE_SPEC.read_bytes()).hexdigest() != '5b614933b8ac9f2afee0f344831e389eec7d0bac23ddde1dcd221feb35b50a93':
        raise ValueError('Round2 hall spec changed')
    base = json.loads(BASE_SPEC.read_text())
    inscriptions = {
      'kings': [('靈鷲飛來', 0, 'kings', 'gold', 'darkglass'), ('雲林禪寺', 1, 'kings', 'gold', 'darkglass')],
      'grand': [('大雄寶殿', 0, 'grand', 'gold', 'darkglass'), ('真如妙相', 1, 'grand', 'gold', 'darkglass')],
      'medicine': [('藥師殿', 0, 'medicine', 'gold', 'darkglass')],
      'dharma': [('直指堂', 0, 'dharma-wide', 'civicred', 'gold'), ('藏經樓', 1, 'dharma-wide', 'gold', 'darkglass')],
      'huayan': [('華嚴殿', 0, 'huayan-wide', 'civicred', 'gold')]
    }
    boards = {hall:[{'text':text, 'tier':tier, 'photoId':photo, 'visualOrder':'right-to-left',
                    'backgroundMaterial':background, 'letterMaterial':letters,
                    'textBasis':'reported operator wording and actually viewed historical reference',
                    'placementBasis':'estimated within frozen facade tiers; no calligraphic facsimile'}
                   for text,tier,photo,background,letters in rows] for hall, rows in inscriptions.items()}
    chars = sorted(set(''.join(row[0] for rows in inscriptions.values() for row in rows)))
    font = ImageFont.truetype(str(args.font), 22)
    glyphs = {}
    sheet = Image.new('RGB', (len(chars)*28, 56), '#ffffff')
    draw = ImageDraw.Draw(sheet)
    for index, char in enumerate(chars):
        image = Image.new('L', (24, 24), 0)
        a,b,c,d = font.getbbox(char)
        ImageDraw.Draw(image).text((1-a,1-b), char, font=font, fill=255)
        glyphs[char] = rectangles(image)
        assert glyphs[char], f'Missing glyph {char}'
        sheet.paste(Image.eval(image,lambda p:255-p).convert('RGB'), (index*28+2, 2))
        draw.text((index*28+8,34), str(index), fill='#333333')
    sheet.save(OUT/'font-glyph-cpu-sheet.png')
    (OUT/'SourceHanSerif-OFL.txt').write_text(args.font_license.read_text())
    lengths = {'kings':8., 'grand':12., 'medicine':7., 'dharma':5., 'huayan':7.}
    drops = {'kings':.5, 'grand':1.2, 'medicine':1.2, 'dharma':4., 'huayan':1.5}
    allowance = {'kings':.5, 'grand':1., 'medicine':1., 'dharma':3., 'huayan':1.2}
    terraces = {}
    for hall in base['halls']:
        key = hall['id']
        terraces[key] = {'widthM':hall['widthM']*.96, 'frontLengthM':lengths[key], 'dropM':drops[key],
          'stairWidthM':10. if key=='grand' else 6., 'treadM':.32, 'nominalMaxRiserM':.18,
          'basis':'estimated', 'observedStepCount':None, 'absoluteThresholdYGame':None,
          'sourcePhotoIds':['dharma-wide'] if key=='dharma' else [key],
          'method':'Small source-registered hall-front apron. Photo-visible masonry plinth/stone balustrades and human-scale context guide a simplified local drop; no calibrated photogrammetry. Width uses .96 of the OSM roof width only as a modelling constraint; front length deliberately limited to avoid invented whole courtyards. Steps are generated from drop/max-riser, not counted in a survey.',
          'uncertainty':{'widthM':5., 'frontLengthM':5., 'dropM':allowance[key], 'treadM':.10,
                         'trueStepCount':'unknown', 'boundsMeaning':'broad modelling allowances, not guaranteed/statistical confidence'},
          'joiningStatus':'pending surveyed floors/current terrain cut and external path validation'}
    spec = {'schemaVersion':1, 'id':'lingyin-temple', 'cityId':'hangzhou', 'siteVersion':3,
      'scope':'Frozen five axial exterior hall shells with caller-supplied per-hall game-unit plinth bases, limited estimated front terraces/stairs, source-transcribed plaque geometry and representative ridge-end details. Not the whole monastery or surveyed ground.',
      'anchor':base['anchor'], 'sourceSnapshotSha256':base['sourceSnapshotSha256'],
      'sourceFeatureIds':base['sourceFeatureIds'], 'baseBuildingIdsToExclude':base['baseBuildingIdsToExclude'],
      'baseHallSpec':base,
      'baseHallModule':'scripts/landmarks/lingyin_temple.py',
      'baseHallModuleSha256':'0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011',
      'baseHallSpecPath':str(BASE_SPEC.relative_to(ROOT)),
      'baseHallSpecSha256':hashlib.sha256(BASE_SPEC.read_bytes()).hexdigest(),
      'baseHallSpecCanonicalSha256':hashlib.sha256(json.dumps(base,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
      'hallBaseYGame':{key:None for key in inscriptions},
      'baseYContract':{'meaning':'absolute game-unit bottom of the frozen .5m plinth; threshold is baseY+.5*.60',
                       'precedence':'explicit build_with_hall_bases argument, else lm.hallBaseYGame, else spec.hallBaseYGame',
                       'lmY':'ignored', 'missing':'raises ValueError before geometry/frame changes',
                       'sourceBasis':'caller-owned external input; no automatic DSM floor assignment'},
      'terraces':terraces, 'inscriptions':boards, 'glyphRectangles':glyphs,
      'glyphSource':{'fontName':'Source Han Serif TC Regular', 'publisher':'Adobe',
        'url':'https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/OTF/TraditionalChinese/SourceHanSerifTC-Regular.otf',
        'sha256':FONT_SHA, 'bytes':args.font.stat().st_size, 'license':'SIL Open Font License 1.1',
        'licensePath':'SourceHanSerif-OFL.txt', 'licenseUrl':'https://raw.githubusercontent.com/adobe-fonts/source-han-serif/release/LICENSE.txt',
        'fontBundled':False, 'pixelTexturesBundled':False,
        'output':'authored nonoverlapping foreground rectangles; geometry embedded in spec, not font/photo texture',
        'method':'22px OpenType FreeType rendering into 24x24 mask; threshold140; identical horizontal runs merged vertically. No photograph tracing.',
        'artisticLimit':'Open serif glyphs approximate wording only; exact historic calligraphy/strokes and colors remain unknown'},
      'detailEstimates':{
        'stoneRails':{'basis':'estimated','sourceIds':['axis-photo-2020','hall-photo-2020'],
          'value':{'heightM':1.,'pitchM':3.,'postWidthM':.24,'panelDepthM':.13},
          'method':'Sparse pale stone posts and two horizontal panel bands around visible local platforms, central stair mouth open; intricate relief is pending.',
          'uncertainty':'height ±.3m; pitch ±1m; true panel count/stone relief unknown'},
        'paving':{'basis':'estimated','sourceIds':['grand-official','dharma-official'],
          'value':{'pitchM':4.},'method':'Limited perpendicular thin geometric seams on the new apron, not copied photograph pixels.',
          'uncertainty':'pitch ±2m, real paving joints/pattern not measured'},
        'ridgeEnds':{'basis':'estimated','sourceIds':['roof-photo-2021'],
          'value':{'segments':3,'curlLengthM':.55,'curlRiseM':.55},
          'method':'Representative pale ceramic upward curl silhouettes supplement old ridge caps; source roof detail hall attribution unknown. Not dragon/chifinial carving reproduction.',
          'uncertainty':'length/rise ±.35m, precise count/direction/form per hall unknown'}},
      'coordinatePolicy':base['coordinatePolicy'],
      'boundary':{'polygonWGS84':None,'basis':'unknown','reference':'heritage layout paper Fig5 and official diagram show contextual enclosure only, not a georeferenced/legal current boundary'},
      'integrationContract':{'replacePriorObject':'lingyin-temple','containsFrozenFiveHallGeometry':True,
        'excludeOnlySourceFeatureIds':base['sourceFeatureIds'],'doNotDelete':'ticket building, nearby paths/parks/whole mountain or all monastery auxiliaries',
        'groundSolids':'ground_footprints returns explicit world-game candidate solids with min/max Y',
        'surfaces':'floor_height_game supports an explicitly selected hall-front terrace/stair only',
        'safeArrival':'unknown; no connected/accessibility/entry assertion, no collision holes in original closed hall shells'},
      'budget':{'maxTriangles':30000,'maxMaterials':8,'lights':0},
      'pendingSubscopes':['actual hall threshold absolute elevations and datum','whole monastery cadastral boundary/current auxiliary buildings',
        'terrace true outlines/step counts/rises/current carving','continuous downhill/uphill routes and accessible arrival',
        'terrain excavation/retaining-wall and source-path joining','original closed hall doors and interiors',
        'accurate painted decoration/calligraphy/per-hall ridge sculpting','current day/night materials','GLB/runtime collision/browser/performance/8 formal checks']}
    write('spec.json', spec)
    print(json.dumps({'glyphs':len(glyphs),'rectangles':sum(len(t) for t in glyphs.values()),
                      'renderedBoardCharacters':sum(len(t['text']) for rows in boards.values() for t in rows)},ensure_ascii=False))


if __name__ == '__main__':
    main()
