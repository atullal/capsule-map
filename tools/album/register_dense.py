import sys,pathlib,json,cv2,numpy as np
import argparse,hashlib,datetime,uuid
p=argparse.ArgumentParser(description="Fit a fresh dense sensor map using homography plus cubic residuals.")
p.add_argument("--run",required=True,type=pathlib.Path)
p.add_argument("--source",type=pathlib.Path,default=pathlib.Path("/Users/atullal/Projects/projection-mapping"))
p.add_argument("--reference",required=True,type=pathlib.Path)
p.add_argument("--roi",help="Optional camera polygon as JSON [[x,y],...]")
p.add_argument("--legacy-shots",action="store_true",help="Explicitly analyze old captures without a session manifest; never implies current alignment")
a=p.parse_args();run=a.run.resolve()
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCE=a.source.resolve()
sys.path.insert(0,str(SOURCE))
import mapping,calibrate
session_path=run/'session.json'
if not session_path.exists() and not a.legacy_shots:raise RuntimeError('Missing capture session; capture a fresh run')
if session_path.exists():
 session=json.loads(session_path.read_text())
 if session['status']!='complete':raise RuntimeError('Incomplete capture session')
 for name,digest in session['shots'].items():
  if hashlib.sha256((run/'shots'/f'{name}.png').read_bytes()).hexdigest()!=digest:raise RuntimeError('Capture changed: '+name)
else:session={'status':'legacy','serial':'unknown','created_at':None}
# Use the source generator's names rather than relying on its prose pattern count.
calibrate.PATTERNS=str(run/'patterns');expected={name for name,_ in calibrate.make_patterns()}
missing=[name for name in expected if not (run/'shots'/f'{name}.png').exists()]
if missing:raise RuntimeError('Missing patterns: '+str(missing))
if session_path.exists() and set(session['shots'])!=expected:raise RuntimeError('Session pattern inventory differs')
final=run/'calib'
if final.exists():raise RuntimeError('Calibration already exists; choose a new run or preserve the old calibration first')
out=run/('calib-pending-'+uuid.uuid4().hex);out.mkdir(parents=True)
reference=cv2.imread(str(a.reference))
if reference is None:raise RuntimeError('Cannot read reference artwork')
ref=cv2.resize(reference,(1400,1400))
view=cv2.imread(str(run/'shots/white.png'))
clahe=cv2.createCLAHE(3,(8,8))
sift=cv2.SIFT_create(nfeatures=20000,contrastThreshold=.015)
kr,dr=sift.detectAndCompute(clahe.apply(cv2.GaussianBlur(cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY),(0,0),2)),None)
if view is None or view.shape[:2]!=(720,1280):raise RuntimeError('Invalid camera image')
mask=np.full(view.shape[:2],255,np.uint8)
if a.roi:
 mask[:]=0;cv2.fillConvexPoly(mask,np.int32(json.loads(a.roi)),255)
if session.get('capture_backend')!='guarded_factory_jpeg':mask[335:373,478:819]=0
kc,dc=sift.detectAndCompute(clahe.apply(cv2.cvtColor(view,cv2.COLOR_BGR2GRAY)),mask)
if dr is None or dc is None:raise RuntimeError('No usable reference features')
good=[pair[0] for pair in cv2.BFMatcher().knnMatch(dr,dc,k=2) if len(pair)==2 and pair[0].distance<.75*pair[1].distance]
if len(good)<60:raise RuntimeError('Insufficient artwork matches')
rp=np.float32([kr[m.queryIdx].pt for m in good]);cp=np.float32([kc[m.trainIdx].pt for m in good])
H,inlier=cv2.findHomography(rp,cp,cv2.USAC_MAGSAC,2.5)
if H is None or inlier is None:raise RuntimeError('Artwork registration failed')
keep=inlier.ravel()>0;rp=rp[keep];cp=cp[keep]
print('SIFT inliers',len(rp),flush=True)
if len(rp)<60:raise RuntimeError('Insufficient artwork matches')
cam2art,keep=mapping.fit_smooth(cp,rp)
res=mapping.apply_smooth(cam2art,cp[keep])-rp[keep]
art_rms=float(np.sqrt((res**2).sum(1).mean()))
if not np.isfinite(art_rms) or art_rms>6:raise RuntimeError('Artwork registration too imprecise')
print('Art registration RMS artwork px',art_rms,flush=True)
shots={p.stem:cv2.cvtColor(cv2.imread(str(p)),cv2.COLOR_BGR2GRAY).astype(np.int16) for p in (run/'shots').glob('*.png')}
px,py,valid,lit=calibrate.decode(shots)
if session.get('capture_backend')!='guarded_factory_jpeg':valid[335:373,478:819]=False
Y,X=np.indices(valid.shape);cam=np.float32(np.stack([X[valid],Y[valid]],1));proj=np.float32(np.stack([px[valid],py[valid]],1))
art=mapping.apply_smooth(cam2art,cam);inside=(art.min(1)>8)&(art.max(1)<1392);cam=cam[inside];proj=proj[inside]
print('Dense surface points',len(cam),flush=True)
if len(cam)<1000:raise RuntimeError('Insufficient decoded surface points')
# Source project's coarse fit + cubic re-admission handles a bowed sleeve without
# depending on an earlier manually marked homography from another physical setup.
_,coarse=cv2.findHomography(cam,proj,cv2.RANSAC,10.0)
if coarse is None or coarse.sum()<1000:raise RuntimeError('No coherent decoded surface')
initial,_=mapping.fit_smooth(cam[coarse.ravel()>0],proj[coarse.ravel()>0])
explained=np.linalg.norm(mapping.apply_smooth(initial,cam)-proj,axis=1)<5
cam=cam[explained];proj=proj[explained]
if len(cam)<2000:raise RuntimeError('Too few consistent surface points')
# Spatially interleaved held-out points measure prediction beyond the fit itself.
hold=(cam[:,0].astype(int)//12+cam[:,1].astype(int)//12)%5==0
check,_=mapping.fit_smooth(cam[~hold],proj[~hold])
held_errors=np.linalg.norm(mapping.apply_smooth(check,cam[hold])-proj[hold],axis=1)
held_rms=float(np.sqrt(np.mean(held_errors**2)))
if not np.isfinite(held_rms) or held_rms>3.5:raise RuntimeError('Held-out mapping error exceeds 3.5 projector pixels')
cam2proj,good=mapping.fit_smooth(cam,proj);cam=cam[good];proj=proj[good]
proj2cam,good=mapping.fit_smooth(proj,cam)
res=mapping.apply_smooth(cam2proj,cam)-proj;rms=float(np.sqrt((res**2).sum(1).mean()));print('Dense projector fit RMS',rms,flush=True)
if not np.isfinite(rms) or rms>3:raise RuntimeError('Dense fit not precise enough')
grid=np.stack(np.meshgrid(np.arange(1920,dtype=np.float32),np.arange(1080,dtype=np.float32)),-1).reshape(-1,2)
camgrid=mapping.apply_smooth(proj2cam,grid);artgrid=mapping.apply_smooth(cam2art,camgrid).reshape(1080,1920,2).astype(np.float32)
if not np.isfinite(artgrid).all():raise RuntimeError('Non-finite projector lookup')
inside=(artgrid[:,:,0]>=8)&(artgrid[:,:,0]<1392)&(artgrid[:,:,1]>=8)&(artgrid[:,:,1]<1392)
artgrid[~inside]=-1
np.savez_compressed(out/'render_map.npz',map_x=artgrid[:,:,0],map_y=artgrid[:,:,1],bbox=[0,0,1920,1080],ref=1400)
cv2.imwrite(str(out/'reference.png'),ref)
sleeve=np.zeros((1400,1400),np.uint8);sleeve[8:-8,8:-8]=255;cv2.imwrite(str(out/'sleeve.png'),sleeve)
covered=np.zeros((1400,1400),np.uint8);covered_pixels=artgrid[inside].astype(int);covered[covered_pixels[:,1],covered_pixels[:,0]]=255;covered=cv2.morphologyEx(covered,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8));cv2.imwrite(str(out/'covered.png'),covered)
edges=cv2.Canny(cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY),80,160);edges=cv2.dilate(edges,np.ones((2,2),np.uint8));test=cv2.remap(cv2.cvtColor(edges,cv2.COLOR_GRAY2BGR),artgrid[:,:,0],artgrid[:,:,1],cv2.INTER_LINEAR);cv2.imwrite(str(out/'edge-test.png'),test)
coverage=float((covered>0).mean())
if coverage<.25:raise RuntimeError('Beam covers less than 25% of artwork')
metrics={'schema':1,'status':'needs_visual_verification','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'capture_status':session['status'],'serial':session['serial'],'reference_sha256':hashlib.sha256(a.reference.read_bytes()).hexdigest(),'sift_inliers':len(rp),'artwork_fit_rms_px':art_rms,'decoded_points':len(cam),'projector_fit_rms_px':rms,'held_out_rms_px':held_rms,'beam_coverage_fraction':coverage,'camera_size':[1280,720],'projector_size':[1920,1080]}
json.dump(metrics,open(out/'metrics.json','w'),indent=2)
np.savez_compressed(out/'models.npz',cam2proj=cam2proj,proj2cam=proj2cam,cam2art=cam2art)

metrics['render_map_sha256']=hashlib.sha256((out/'render_map.npz').read_bytes()).hexdigest()
(out/'metrics.json').write_text(json.dumps(metrics,indent=2))
out.rename(final)
print(json.dumps(metrics,indent=2))
