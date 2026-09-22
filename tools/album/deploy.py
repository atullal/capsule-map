"""Encode and deploy a verified calibration-bound loop, checking the transfer checksum."""
import argparse,hashlib,json,pathlib,re,subprocess,urllib.request
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--serial',required=True);p.add_argument('--name',required=True);a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.mp4',a.name):raise RuntimeError('Choose a simple .mp4 filename')
run=a.run.resolve();metrics=json.loads((run/'calib/metrics.json').read_text());render=json.loads((run/'render.json').read_text())
digest=hashlib.sha256((run/'calib/render_map.npz').read_bytes()).hexdigest()
if digest!=render['render_map_sha256'] or digest!=metrics['render_map_sha256'] or metrics['status']!='visually_verified':raise RuntimeError('Render and verified calibration do not match')
if len(list((run/'frames').glob('f*.jpg')))!=render['frames']:raise RuntimeError('Incomplete frame sequence')
for i in range(render['frames']):
 if not (run/'frames'/f'f{i:04d}.jpg').is_file():raise RuntimeError('Missing frame '+str(i))
video=run/a.name
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(render['fps']),'-i',str(run/'frames/f%04d.jpg'),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
video_sha=hashlib.sha256(video.read_bytes()).hexdigest();metadata=dict(metrics,media_sha256=video_sha,render=render)
meta=run/(a.name+'.json');meta.write_text(json.dumps(metadata,indent=2))
def adb(*args):return subprocess.check_output(['adb','-s',a.serial,*args],text=True,timeout=90)
remote='/sdcard/Android/data/dev.atul.capsulemap/files/'
# Stage and hash-check both files before replacing the playable name.
for local,name in [(video,a.name),(meta,a.name+'.json')]:
 adb('push',str(local),remote+name+'.pending')
 actual=adb('shell','sha256sum',remote+name+'.pending').split()[0]
 if actual!=hashlib.sha256(local.read_bytes()).hexdigest():raise RuntimeError('Transfer checksum mismatch')
for name in [a.name+'.json',a.name]:adb('shell','mv',remote+name+'.pending',remote+name)
print(adb('shell','am','start','-W','-n','dev.atul.capsulemap/.MediaActivity','--es','file',a.name))
print('Deployed',a.name,video_sha)
