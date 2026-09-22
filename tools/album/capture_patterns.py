"""Capture a fresh, isolated Gray-code session through the internal Nebula sensor."""
import argparse, datetime, hashlib, json, pathlib, subprocess, sys, time
import cv2
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/camera'));from sensor import Sensor
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('serial');p.add_argument('--source',type=pathlib.Path,default=(pathlib.Path(__file__).resolve().parents[2]/'vendor/projection-mapping'))
p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--resume-media',default='life-and-love.mp4')
p.add_argument('--backend',choices=['projector','host'],default='projector',help='Projector-local batch is the default; host preserves the earlier per-photo path')
a=p.parse_args();run=a.run.resolve()
if a.backend=='projector':
 raise SystemExit(subprocess.call([sys.executable,str(ROOT/'tools/camera/batch.py'),'--serial',a.serial,'--run',str(run),'--resume-media',a.resume_media]))
# Never silently mix photographs from different physical setups.
run.mkdir(parents=True,exist_ok=False);(run/'shots').mkdir()
sys.path.insert(0,str(a.source.resolve()));import calibrate
calibrate.PATTERNS=str(run/'patterns');items=calibrate.make_patterns()
manifest={'schema':1,'serial':a.serial,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'capturing','capture_backend':'guarded_factory_jpeg','camera_size':[1280,720],'projector_size':[1920,1080],'patterns':[name for name,_ in items],'shots':{},'source_sha256':hashlib.sha256((a.source/'calibrate.py').read_bytes()).hexdigest()}
def save():
 temp=run/'session.tmp';temp.write_text(json.dumps(manifest,indent=2));temp.replace(run/'session.json')
def adb(*args):
 r=subprocess.run(['adb','-s',a.serial,*args],capture_output=True,text=True,timeout=30)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
def show(file):adb('shell','am','start','-W','-n','dev.atul.capsulemap/.MediaActivity','--es','file',file)
save()
sensor=Sensor(a.serial)
try:
 adb('push',*[path for _,path in items],'/sdcard/Android/data/dev.atul.capsulemap/files/')
 for name,_ in items:
  show(name+'.png');time.sleep(.6)
  raw=run/'capture.jpg';sensor.capture(raw)
  im=cv2.imread(str(raw))
  if im is None or im.shape[:2]!=(720,1280):raise RuntimeError('Unexpected internal-camera dimensions')
  im=cv2.rotate(im,cv2.ROTATE_180);out=run/'shots'/f'{name}.png'
  if not cv2.imwrite(str(out),im):raise RuntimeError('Cannot save camera image')
  manifest['shots'][name]=hashlib.sha256(out.read_bytes()).hexdigest();save()
  print('captured',name,flush=True)
 manifest['status']='complete';save()
except BaseException as e:
 manifest['status']='failed';manifest['error']=str(e);save();raise
finally:
 try:show(a.resume_media)
 except Exception as e:print('Could not restore media:',e,file=sys.stderr)
print(run)
