"""One fresh structured-light capture, three independently registered artwork maps."""
import argparse,pathlib,sys,json,hashlib,datetime
import cv2,numpy as np
from registration import register
p=argparse.ArgumentParser();p.add_argument('--capture',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--references',type=pathlib.Path,required=True);a=p.parse_args()
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'vendor/projection-mapping'));import calibrate,mapping
run=a.capture;session=json.loads((run/'session.json').read_text())
if session['status']!='complete':raise RuntimeError('Capture incomplete')
for name,sha in session['shots'].items():
 if hashlib.sha256((run/'shots'/f'{name}.png').read_bytes()).hexdigest()!=sha:raise RuntimeError('Capture changed')
shots={name:cv2.imread(str(run/'shots'/f'{name}.png'),0).astype(np.int16) for name in session['patterns']}
px,py,valid,_=calibrate.decode(shots)
exclude_overlay=session.get('capture_backend')!='guarded_factory_jpeg'
if exclude_overlay:valid[333:376,476:822]=False
view=cv2.imread(str(run/'shots/white.png'));a.output.mkdir(parents=True,exist_ok=True)
rois={'life':[[320,287],[513,289],[505,476],[320,470]],'hox':[[524,295],[711,295],[710,482],[521,480]],'crimson':[[713,298],[907,300],[912,485],[713,485]]}
grid=np.stack(np.meshgrid(np.arange(1920,dtype=np.float32),np.arange(1080,dtype=np.float32)),-1).reshape(-1,2)
reports={};combined=np.zeros((1080,1920,3),np.uint8)
for name,roi in rois.items():
 out=a.output/name/'calib'
 if out.exists():raise RuntimeError('Refusing to replace existing '+str(out))
 ref=cv2.resize(cv2.imread(str(a.references/(name+'.jpg'))),(1400,1400))
 H,report,mask=register(ref,view,roi,exclude_overlay=exclude_overlay);print(name,report,flush=True)
 cam2art=np.linalg.inv(H)
 ys,xs=np.nonzero(valid & (mask>0));cam=np.float32(np.stack([xs,ys],1));proj=np.float32(np.stack([px[ys,xs],py[ys,xs]],1))
 art=cv2.perspectiveTransform(cam[None],cam2art)[0];inside=(art.min(1)>12)&(art.max(1)<1388);cam=cam[inside];proj=proj[inside]
 _,coarse=cv2.findHomography(cam,proj,cv2.RANSAC,10)
 model,_=mapping.fit_smooth(cam[coarse.ravel()>0],proj[coarse.ravel()>0]);good=np.linalg.norm(mapping.apply_smooth(model,cam)-proj,axis=1)<5;cam=cam[good];proj=proj[good]
 hold=(cam[:,0].astype(int)//8+cam[:,1].astype(int)//8)%5==0
 model,_=mapping.fit_smooth(cam[~hold],proj[~hold]);err=np.linalg.norm(mapping.apply_smooth(model,cam[hold])-proj[hold],axis=1);held=float(np.sqrt((err**2).mean()))
 model,good=mapping.fit_smooth(cam,proj);cam=cam[good];proj=proj[good];inverse,_=mapping.fit_smooth(proj,cam)
 rms=float(np.sqrt(((mapping.apply_smooth(model,cam)-proj)**2).sum(1).mean()))
 if len(cam)<1500 or held>3.5 or rms>3:raise RuntimeError(name+' dense fit failed: '+str((len(cam),held,rms)))
 artgrid=cv2.perspectiveTransform(mapping.apply_smooth(inverse,grid).astype(np.float32)[None],cam2art)[0].reshape(1080,1920,2)
 inside=(artgrid.min(2)>=16)&(artgrid.max(2)<1384);artgrid[~inside]=-1
 out.mkdir(parents=True);np.savez_compressed(out/'render_map.npz',map_x=artgrid[:,:,0],map_y=artgrid[:,:,1],bbox=[0,0,1920,1080],ref=1400)
 cv2.imwrite(str(out/'reference.png'),ref);sleeve=np.zeros((1400,1400),np.uint8);sleeve[16:-16,16:-16]=255;cv2.imwrite(str(out/'sleeve.png'),sleeve)
 covered=np.zeros((1400,1400),np.uint8);points=artgrid[inside].astype(int);covered[points[:,1],points[:,0]]=255;covered=cv2.morphologyEx(covered,cv2.MORPH_CLOSE,np.ones((13,13),np.uint8));cv2.imwrite(str(out/'covered.png'),covered)
 # Smooth the source texture before extracting contours so the diagnostic is readable.
 edges=cv2.Canny(cv2.GaussianBlur(ref,(0,0),1.2),65,140);edges=cv2.dilate(edges,np.ones((3,3),np.uint8));test=cv2.remap(cv2.cvtColor(edges,cv2.COLOR_GRAY2BGR),artgrid[:,:,0],artgrid[:,:,1],cv2.INTER_LINEAR);combined=np.maximum(combined,test)
 report.update(decoded_points=len(cam),projector_fit_rms_px=rms,held_out_rms_px=held,beam_coverage_fraction=float((covered>0).mean()),render_map_sha256=hashlib.sha256((out/'render_map.npz').read_bytes()).hexdigest(),status='needs_visual_verification')
 (out/'metrics.json').write_text(json.dumps(report,indent=2));reports[name]=report;print(name,'dense RMS',rms,'held',held,'coverage',report['beam_coverage_fraction'],flush=True)
cv2.imwrite(str(a.output/'edge-test.png'),combined);(a.output/'calibration.json').write_text(json.dumps(reports,indent=2))
