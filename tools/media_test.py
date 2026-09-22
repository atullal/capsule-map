"""Device integration check for media failure recovery and restart persistence."""
import argparse,json,pathlib,subprocess,tempfile,time,urllib.request
p=argparse.ArgumentParser();p.add_argument('--serial',required=True);p.add_argument('--host',required=True);p.add_argument('--pin',required=True);a=p.parse_args();base='http://'+a.host+':8765'
def adb(*cmd):return subprocess.check_output(['adb','-s',a.serial,*cmd],text=True,timeout=30)
def state():return json.load(urllib.request.urlopen(base+'/state',timeout=10))
def post(path,obj):
 obj['pin']=a.pin
 return json.load(urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(obj).encode(),headers={'Content-Type':'application/json'}),timeout=10))
def wait_status(expected):
 for _ in range(30):
  v=state()
  if v['media']['status']==expected:return v
  time.sleep(.2)
 raise AssertionError(v)
old=state();remote='/sdcard/Android/data/dev.atul.capsulemap/files/invalid-test.mp4'
try:
 with tempfile.TemporaryDirectory() as tmp:
  bad=pathlib.Path(tmp)/'invalid-test.mp4';bad.write_bytes(b'This is deliberately invalid media for recovery testing.')
  adb('push',str(bad),remote)
 post('/media',{'action':'play','file':'invalid-test.mp4'});v=wait_status('error');assert v['media']['error']
 post('/media',{'action':'play','file':'life-and-love.mp4'});wait_status('playing')
 # Temporary factory-camera interruption should return to the same player without
 # a second play command. Do not inspect private app state or assume /state implies decoding.
 adb('shell','am','start','-W','-n','com.zhixin.factorytest/.activity.devicecontrol.DeviceControlTestActivity','--es','fragmentClassName','com.zhixin.factorytest.activity.devicecontrol.CameraHWShootFragment','--es','cmd','playback_recovery_check')
 time.sleep(1);adb('shell','input','keyevent','4');wait_status('playing')
 post('/media',{'action':'stop'});assert state()['mode']==old['mappingMode']
 before=state();adb('shell','am','force-stop','dev.atul.capsulemap');adb('shell','am','start','-W','-n','dev.atul.capsulemap/.MainActivity')
 for _ in range(20):
  try:after=state();break
  except Exception:time.sleep(.2)
 for key in ['prompt','corners','guides','mappingMode']:assert before[key]==after[key],key
 # Same PIN must remain usable after process restart.
 post('/media',{'action':'play','file':'life-and-love.mp4'});wait_status('playing')
 print('PASS: corrupt media error reported, valid media recovers, factory camera interruption resumes, stop returns to mapping, restart preserves mapping and PIN')
finally:
 adb('shell','rm','-f',remote)
