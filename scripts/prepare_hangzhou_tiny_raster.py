"""Create deterministic 8x8 test bytes without decoding or creating an image UI."""
import json,hashlib,struct,zlib
from pathlib import Path
root=Path('artifacts/cities/hangzhou/stability-p1-tiny-v1');root.mkdir(parents=True,exist_ok=False)
raw=b''.join(b'\0'+bytes(v for x in range(8) for v in [x*29+7,y*23+11,(x+y)*13+3,255]) for y in range(8))
def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',8,8,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
(root/'fixture-8x8.png').write_bytes(png)
(root/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>杭城之行 · 微型图片验证</title><link rel="stylesheet" href="/tiny-raster.css"><main><p>GTA_HZ · 受控诊断 P1</p><h1>一次 8×8 像素验证</h1><p>仅测试原生图片解码、像素读取和释放。不会载入城市或创建 WebGL；完整试玩仍未开放。</p><button id="run">开始一次验证</button><button id="stop" disabled>停止</button><pre id="result" role="status">等待手动开始。每次页面加载只允许运行一次。</pre></main><script type="module" src="/tiny-raster.js"></script></html>',encoding='utf-8')
(root/'tiny-raster.css').write_text('body{font:16px system-ui;background:#122128;color:#edf4f5;margin:0}main{max-width:700px;margin:48px auto;padding:24px}button{padding:10px 18px;margin-right:8px;font:inherit}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#20343e;padding:20px;line-height:1.6}h1{font-size:28px}',encoding='utf-8')
report={'width':8,'height':8,'rgbaBytes':256,'pngBytes':len(png),'pngSha256':hashlib.sha256(png).hexdigest(),'browserValidated':False,'requiresManualClick':True,'webgl':False}
(root/'fixture.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
