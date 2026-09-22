"""Read the Nebula factory camera JPEG while holding the current projection over its UI.
Requires the installed Capsule Map capture-guard service and camera bridge.
"""
import contextlib,fcntl,json,pathlib,subprocess,tempfile,time,urllib.request
APP='dev.atul.capsulemap'
REMOTE='/sdcard/Android/data/'+APP+'/files'
FACTORY='com.zhixin.factorytest'
class Sensor:
 def __init__(self,serial):self.serial=serial
 def adb(self,*args,check=True):
  r=subprocess.run(['adb','-s',self.serial,*args],text=True,capture_output=True,timeout=20)
  if check and r.returncode:raise RuntimeError(r.stdout+r.stderr)
  return r.stdout
 def capture(self,output,diagnostics=None):
  output=pathlib.Path(output);output.parent.mkdir(parents=True,exist_ok=True)
  # Concurrent callers must not replace the held frame or consume each other's JPEG.
  import hashlib
  lock=pathlib.Path(tempfile.gettempdir())/('capsule-camera-'+hashlib.sha256(self.serial.encode()).hexdigest()[:16]+'.lock')
  with lock.open('w') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX)
   start=time.monotonic();result=self._capture(output,diagnostics);result["total_seconds"]=time.monotonic()-start;return result
 def _capture(self,output,diagnostics=None):
  port=self.adb('forward','tcp:0','tcp:8765').strip();url='http://127.0.0.1:'+port+'/state'
  def state():return json.load(urllib.request.urlopen(url,timeout=3))
  t=time.monotonic();launched=False;guard=False;saved=None;device_locked=False
  try:
   # Atomic on-device exclusion also covers other laptops and ADB serial aliases.
   self.adb('shell','mkdir',REMOTE+'/capture-batch.lock');device_locked=True
   initial=state()
   ready_until=time.monotonic()+3
   while initial["mode"]=="media" and initial["media"]["status"]=="loading" and time.monotonic()<ready_until:
    time.sleep(.05);initial=state()
   if initial.get('captureGuard') in ('holding','starting'):raise RuntimeError('Another projection hold is active')
   saved=initial['media']['file'] if initial['mode']=='media' else None
   result=self.adb('shell','am','startservice','-n',APP+'/.CaptureGuardService','--ez','prepare','true')
   if 'Error' in result:raise RuntimeError(result)
   guard=True
   deadline=time.monotonic()+3
   while time.monotonic()<deadline:
    status=state().get('captureGuard','unavailable')
    if status=='holding':break
    if status.startswith('error:'):raise RuntimeError(status)
    time.sleep(.05)
   else:raise RuntimeError('Projection guard not ready; camera not opened')
   if diagnostics is not None:
    self.adb('shell','screencap','-p',REMOTE+'/capture-hold.png')
   remote_dir='/sdcard/factorytest/camera_shoot'
   before=set(self.adb('shell','ls',remote_dir,check=False).split())
   self.adb('shell','am','start','-n','dev.atul.camerabridge/.CaptureActivity');launched=True
   deadline=time.monotonic()+7
   while time.monotonic()<deadline:
    fresh=set(self.adb('shell','ls',remote_dir,check=False).split())-before
    names=sorted(n for n in fresh if n.endswith('--calibration_shoot.jpg'))
    if names:break
    time.sleep(.08)
   else:raise RuntimeError('Camera did not save a new JPEG')
   source=remote_dir+'/'+names[-1]
   if diagnostics is not None:
    diagnostics=pathlib.Path(diagnostics);diagnostics.mkdir(parents=True,exist_ok=True)
    self.adb('shell','screencap','-p',REMOTE+'/capture-during.png')
    self.adb('pull',REMOTE+'/capture-during.png',str(diagnostics/'during.png'))
    self.adb('pull',REMOTE+'/capture-hold.png',str(diagnostics/'held.png'))
   # Wait for completed output, not for a preview window or an arbitrary long sleep.
   previous=None
   while time.monotonic()<deadline:
    size=self.adb('shell','stat','-c','%s',source).strip()
    if size==previous and size.isdigit() and int(size)>0:break
    previous=size;time.sleep(.06)
   self.adb('pull',source,str(output))
   data=output.read_bytes()
   if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):raise RuntimeError('Incomplete camera JPEG')
   return {'file':str(output.resolve()),'capture_seconds':time.monotonic()-t,'source':source,'preview_displayed':False}
  finally:
   if launched:
    # Stop only the factory capture process; the held projection remains visible.
    activities=self.adb('shell','dumpsys','activity','activities',check=False)
    factory_on_top=any(FACTORY in line and ('topResumedActivity' in line or 'mResumedActivity' in line) for line in activities.splitlines())
    if factory_on_top:self.adb('shell','input','keyevent','4',check=False)
    else:self.adb('shell','am','force-stop',FACTORY,check=False)
    if saved:
     self.adb('shell','am','start','-n',APP+'/.MediaActivity','--ez','resumeOnly','true',check=False)
    else:self.adb('shell','am','start','-n',APP+'/.MainActivity','-f','0x10020000',check=False)
    until=time.monotonic()+2
    while time.monotonic()<until:
     try:
      if not saved or state()['media']['status'] in ('playing','showing','error'):break
     except Exception:pass
     time.sleep(.05)
   if guard:self.adb('shell','am','stopservice','-n',APP+'/.CaptureGuardService',check=False)
   if device_locked:self.adb('shell','rmdir',REMOTE+'/capture-batch.lock',check=False)
   self.adb('forward','--remove','tcp:'+port,check=False)
