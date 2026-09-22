"""Checksum-verified deployment of the three-sleeve show and its calibration report."""
import argparse,pathlib,json,hashlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--serial',required=True);a=p.parse_args();run=a.run.resolve()
render=json.loads((run/'render.json').read_text());verification=json.loads((run/'verification.json').read_text())
if hashlib.sha256((run/'edge-verification.png').read_bytes()).hexdigest()!=verification['photo_sha256']:raise RuntimeError('Verification photo changed')
for name,report in render['calibration'].items():
 if hashlib.sha256((run/name/'calib/render_map.npz').read_bytes()).hexdigest()!=report['render_map_sha256']:raise RuntimeError('Calibration no longer matches render')
for i in range(render['frames']):
 if not (run/'frames'/f'f{i:04d}.jpg').is_file():raise RuntimeError('Missing frame')
video=run/'three-vinyls.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(render['fps']),'-i',str(run/'frames/f%04d.jpg'),'-frames:v',str(render['frames']),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(video)],text=True))
if abs(float(probe['format']['duration'])-render['duration_seconds'])>.05:raise RuntimeError('Encoded duration mismatch')
reports=render['calibration'];metadata={'schema':1,'status':'visually_verified','surface_count':len(reports),'surfaces':reports,'verification':verification,'held_out_rms_px':max(r['held_out_rms_px'] for r in reports.values()),'beam_coverage_fraction':min(r['beam_coverage_fraction'] for r in reports.values()),'coverage_note':'Includes intentional inset at sleeve edges; all three sleeves are inside the beam.','media_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'render':{k:v for k,v in render.items() if k!='calibration'}}
meta=run/'three-vinyls.mp4.json';meta.write_text(json.dumps(metadata,indent=2))
def adb(*args):return subprocess.check_output(['adb','-s',a.serial,*args],text=True,timeout=90)
remote='/sdcard/Android/data/dev.atul.capsulemap/files/'
for path in [video,meta]:
 adb('push',str(path),remote+path.name+'.pending')
 if adb('shell','sha256sum',remote+path.name+'.pending').split()[0]!=hashlib.sha256(path.read_bytes()).hexdigest():raise RuntimeError('Transfer checksum mismatch')
for path in [meta,video]:adb('shell','mv',remote+path.name+'.pending',remote+path.name)
print(adb('shell','am','start','-W','-n','dev.atul.capsulemap/.MediaActivity','--es','file',video.name))
print('Installed',video.name,probe['format']['duration'],'seconds; SHA256',metadata['media_sha256'])
