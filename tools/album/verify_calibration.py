"""Record an operator's visual edge-projection check, bound to the exact lookup and photo.
This does not automatically judge optical alignment. Inspect the photograph first.
"""
import argparse,datetime,hashlib,json,pathlib,shutil
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=pathlib.Path,required=True);p.add_argument('--photo',type=pathlib.Path,required=True);p.add_argument('--note',required=True);a=p.parse_args()
run=a.run.resolve();path=run/'calib/metrics.json';data=json.loads(path.read_text())
if hashlib.sha256((run/'calib/render_map.npz').read_bytes()).hexdigest()!=data['render_map_sha256']:raise RuntimeError('Map changed after fitting')
if not a.photo.is_file():raise RuntimeError('Verification photo missing')
photo=run/'edge-verification.png'
if a.photo.resolve()!=photo:shutil.copyfile(a.photo,photo)
data['status']='visually_verified';data['verification']={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'photo':photo.name,'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'note':a.note}
temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2));temp.replace(path)
print('Visual verification recorded for',data['render_map_sha256'])
