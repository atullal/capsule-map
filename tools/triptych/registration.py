"""Register distant album prints with multi-scale features and masked photometric refinement."""
import cv2,numpy as np

def register(reference,view,roi,exclude_overlay=True):
 gray=cv2.cvtColor(view,cv2.COLOR_BGR2GRAY);ref=cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY)
 camera_mask=np.zeros(gray.shape,np.uint8);cv2.fillConvexPoly(camera_mask,np.int32(roi),255)
 if exclude_overlay:camera_mask[333:376,476:822]=0
 clahe=cv2.createCLAHE(3,(8,8));sift=cv2.SIFT_create(20000,contrastThreshold=.01)
 kc,dc=sift.detectAndCompute(clahe.apply(gray),camera_mask)
 if dc is None:raise RuntimeError('No camera features')
 src=[];dst=[]
 for size in [280,350,500,700]:
  rr=cv2.resize(ref,(size,size));kr,dr=sift.detectAndCompute(clahe.apply(cv2.GaussianBlur(rr,(0,0),.8)),None)
  if dr is None:continue
  for pair in cv2.BFMatcher().knnMatch(dr,dc,k=2):
   if len(pair)==2 and pair[0].distance<.78*pair[1].distance:
    m=pair[0];src.append(np.array(kr[m.queryIdx].pt)*1400/size);dst.append(kc[m.trainIdx].pt)
 src=np.float32(src);dst=np.float32(dst)
 if len(src)<18:raise RuntimeError('Insufficient artwork features')
 H,keep=cv2.findHomography(src,dst,cv2.USAC_MAGSAC,1.5);keep=keep.ravel()>0;src=src[keep];dst=dst[keep]
 # Multiple scales may rediscover one point: count each sensor location only once.
 _,unique=np.unique(np.round(dst).astype(int),axis=0,return_index=True);src=src[unique];dst=dst[unique]
 if len(src)<18:raise RuntimeError('Too few distinct reference matches')
 H,_=cv2.findHomography(src,dst,0)
 corners=cv2.perspectiveTransform(np.float32([[[0,0],[1400,0],[1400,1400],[0,1400]]]),H)[0]
 if not cv2.isContourConvex(corners.astype(np.float32)) or cv2.contourArea(corners)<4000:raise RuntimeError('Degenerate artwork registration')
 if cv2.contourArea(cv2.convexHull(src))/(1400**2)<.15:raise RuntimeError('Reference matches clustered in too small an area')
 err=np.linalg.norm(cv2.perspectiveTransform(src[None],H)[0]-dst,axis=1)
 initial_rms=float(np.sqrt((err**2).mean()))
 if initial_rms>1.3:raise RuntimeError('Feature fit above 1.3 camera pixels')
 # Rectify the physical print to artwork coordinates, then refine residual projective
 # registration. The factory success text is omitted from the correlation mask.
 size=350;A=np.diag([size/1400,size/1400,1.]);Hsmall=H@np.linalg.inv(A)
 rect=cv2.warpPerspective(gray,np.linalg.inv(Hsmall),(size,size))
 valid=cv2.warpPerspective(camera_mask,np.linalg.inv(Hsmall),(size,size));valid=cv2.erode(valid,np.ones((7,7),np.uint8));valid[:6]=0;valid[-6:]=0;valid[:,:6]=0;valid[:,-6:]=0
 target=cv2.resize(ref,(size,size));target=clahe.apply(target);rect=clahe.apply(rect)
 correction=np.eye(3,dtype=np.float32);cc=None
 try:
  cc,correction=cv2.findTransformECC(target.astype(np.float32)/255,rect.astype(np.float32)/255,correction,cv2.MOTION_HOMOGRAPHY,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,150,1e-6),valid,5)
  candidate=Hsmall@correction@A
  moved=np.linalg.norm(cv2.perspectiveTransform(np.float32([[[0,0],[1400,0],[1400,1400],[0,1400]]]),candidate)[0]-corners,axis=1)
  candidate_err=np.linalg.norm(cv2.perspectiveTransform(src[None],candidate)[0]-dst,axis=1)
  if cc>.65 and moved.max()<5 and np.sqrt((candidate_err**2).mean())<1.5:H=candidate
 except cv2.error:pass
 corners=cv2.perspectiveTransform(np.float32([[[0,0],[1400,0],[1400,1400],[0,1400]]]),H)[0]
 return H,{'unique_sift_inliers':len(src),'feature_rms_camera_px':initial_rms,'ecc_correlation':None if cc is None else float(cc),'camera_corners':corners.tolist()},camera_mask
