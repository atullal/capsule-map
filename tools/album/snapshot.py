"""Photograph the projection without displaying the captured image on the projector."""
import argparse,json,pathlib,sys,tempfile,time,cv2
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'camera'))
from sensor import Sensor
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serial',required=True);p.add_argument('--output',required=True,type=pathlib.Path);p.add_argument('--resume');p.add_argument('--seek-ms',type=int);p.add_argument('--settle-seconds',type=float,default=.3);a=p.parse_args()
time.sleep(max(0,min(a.settle_seconds,10)))
sensor=Sensor(a.serial)
with tempfile.TemporaryDirectory() as temp:
 raw=pathlib.Path(temp)/'sensor.jpg';report=sensor.capture(raw)
 im=cv2.imread(str(raw))
 if im is None or im.shape[:2]!=(720,1280):raise RuntimeError('Unexpected internal camera dimensions')
 im=cv2.rotate(im,cv2.ROTATE_180);a.output.parent.mkdir(parents=True,exist_ok=True)
 if not cv2.imwrite(str(a.output),im):raise RuntimeError('Could not save photograph')
# Normal capture preserves playback; a requested explicit offset is still supported.
if a.resume and a.seek_ms is not None:sensor.adb('shell','am','start','-n','dev.atul.capsulemap/.MediaActivity','--es','file',a.resume,'--ei','seekMs',str(a.seek_ms))
report['file']=str(a.output.resolve());print(json.dumps(report,indent=2))
