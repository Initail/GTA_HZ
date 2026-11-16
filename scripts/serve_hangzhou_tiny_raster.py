"""Same bounded server; only the opt-in 8x8 2D experiment is exposed."""
import serve_hangzhou_recovery as server
server.SERVICE='tiny-raster-no-webgl'
server.FILES={'/tiny-raster.html':('index.html','text/html; charset=utf-8'),
 '/tiny-raster.js':('tiny-raster.js','text/javascript; charset=utf-8'),
 '/tiny-raster.css':('tiny-raster.css','text/css; charset=utf-8'),
 '/fixture-8x8.png':('fixture-8x8.png','image/png')}
if __name__=='__main__':server.main()
