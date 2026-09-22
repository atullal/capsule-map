"""Exercise calibration failure guards without using or changing the projector."""
import argparse,json,pathlib,subprocess,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--reference',type=pathlib.Path,required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
def rejected(script,args,reason):
 r=subprocess.run([sys.executable,str(root/'tools/album'/script),*args],capture_output=True,text=True)
 assert r.returncode!=0 and reason in r.stderr,(r.stdout,r.stderr)
with tempfile.TemporaryDirectory() as tmp:
 run=pathlib.Path(tmp);args=['--run',str(run),'--reference',str(a.reference)]
 rejected('register_dense.py',args,'Missing capture session')
 (run/'session.json').write_text(json.dumps({'status':'failed'}));rejected('register_dense.py',args,'Incomplete capture session')
 (run/'shots').mkdir();(run/'shots/white.png').write_bytes(b'changed')
 (run/'session.json').write_text(json.dumps({'status':'complete','shots':{'white':'incorrect'}}));rejected('register_dense.py',args,'Capture changed')
 rejected('capture_patterns.py',['unused-device','--run',str(run)],'FileExistsError')
 rejected('deploy.py',['--run',str(run),'--serial','unused','--name','../bad.mp4'],'Choose a simple')
rejected('register_dense.py',['--run',str(a.run),'--reference',str(a.reference)],'Calibration already exists')
print('PASS: missing, incomplete and changed captures rejected; existing runs/calibrations preserved; unsafe deployment name rejected')
