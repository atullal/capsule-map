"""Three independent artwork-space animations composed once into the projector framebuffer."""
import argparse,pathlib,sys,multiprocessing,json,hashlib
import cv2,numpy as np
HERE=pathlib.Path(__file__).resolve().parent
# Avoid this wrapper's render.py shadowing the source project's render module.
sys.path.insert(0,'/Users/atullal/Projects/projection-mapping')
import animate as life,animate_hox as hox,animate_hox_show as hoxshow,animkit
import importlib.util
spec=importlib.util.spec_from_file_location('source_warp','/Users/atullal/Projects/projection-mapping/render.py');warp_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(warp_module)
spec=importlib.util.spec_from_file_location('crimson_animation',HERE/'crimson.py');crimson=importlib.util.module_from_spec(spec);spec.loader.exec_module(crimson)
p=argparse.ArgumentParser();p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--sheet',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--workers',type=int,default=4);a=p.parse_args();RUN=a.run.resolve()
FPS=30;LOOP=28.8;FRAMES=864
warps={}
def setup():
 cv2.setNumThreads(1)
 import render as source_render
 source_render.CALIB=str(RUN/'life/calib');life.CALIB=source_render.CALIB;life.setup()
 hox.CALIB=str(RUN/'hox/calib');hox.FIELDS=str(RUN/'hox/calib/hox_fields.npz');animkit.CALIB=hox.CALIB
 hoxshow.SCENES=[hoxshow.ignition,hoxshow.radar,hoxshow.data_rain,hoxshow.spotlights_finale];hoxshow.TOTAL=LOOP;hoxshow.setup()
 animkit.CALIB=str(RUN/'crimson/calib');crimson.setup(RUN/'crimson/calib/reference.png',animkit.beam_alpha())
 for name in ['life','hox','crimson']:
  warp_module.CALIB=str(RUN/name/'calib');warps[name]=warp_module.ProjectorWarp()
def lights(t):
 fade=animkit.smoothstep(t/.6)*(1-animkit.smoothstep((t-(LOOP-.7))/.7))
 return {'life':life.frame_light((t%14.4)*16/14.4)*fade,'hox':hoxshow.frame_light(t)*fade,'crimson':crimson.frame_light(t)}
def frame(i):
 canvas=np.zeros((1080,1920,3),np.uint8)
 for name,light in lights(i/FPS).items():
  image=np.uint8(np.clip(light,0,1)*255+.5);canvas=np.maximum(canvas,warps[name].full(image))
 if not cv2.imwrite(str(RUN/'frames'/f'f{i:04d}.jpg'),canvas,[cv2.IMWRITE_JPEG_QUALITY,94]):raise RuntimeError('Frame write failed')
 return i
if __name__=='__main__':
 metrics=json.loads((RUN/'calibration.json').read_text())
 for name,m in metrics.items():
  if hashlib.sha256((RUN/name/'calib/render_map.npz').read_bytes()).hexdigest()!=m['render_map_sha256']:raise RuntimeError('Changed calibration '+name)
 if a.prepare:
  hox.CALIB=str(RUN/'hox/calib');hox.FIELDS=str(RUN/'hox/calib/hox_fields.npz');hox.build_fields()
 elif a.sheet:
  setup();rows=[]
  for t in [0,2.4,5.4,9.6,14.4,20.4,25.8,LOOP-1/FPS]:
   tiles=[]
   for name,light in lights(t).items():
    tile=cv2.resize(np.uint8(np.clip(light,0,1)*255),(350,350));cv2.putText(tile,f'{name} / {t:.2f}s',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1);tiles.append(tile)
   rows.append(np.hstack(tiles))
  cv2.imwrite(str(RUN/'contact-sheet.jpg'),np.vstack(rows))
 else:
  verified=json.loads((RUN/'verification.json').read_text())
  if hashlib.sha256((RUN/'edge-verification.png').read_bytes()).hexdigest()!=verified['photo_sha256']:raise RuntimeError('Verification photo changed')
  (RUN/'frames').mkdir(exist_ok=True);(RUN/'render.json').unlink(missing_ok=True)
  with multiprocessing.Pool(a.workers,initializer=setup) as pool:
   for count,_ in enumerate(pool.imap_unordered(frame,range(FRAMES),chunksize=4),1):
    if count%72==0:print('rendered',count,'/',FRAMES,flush=True)
  (RUN/'render.json').write_text(json.dumps({'fps':FPS,'frames':FRAMES,'duration_seconds':LOOP,'beats':48,'frames_per_beat':18,'calibration':metrics},indent=2))
