#!/usr/bin/env python3
"""Map manually selected camera-image corners into projector coordinates.
Coordinates refer to the raw sensor image rotated 180 degrees. Calibration's
four points are the full white factory-screen corners, TL/TR/BR/BL. Target
points lie on the same flat wall. No depth or lens-distortion model is estimated.
"""
import argparse,json,pathlib
import cv2
import numpy as np
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--image',required=True,type=pathlib.Path)
p.add_argument('--calibration',required=True,help='JSON array of four image xy points')
p.add_argument('--target',required=True,help='JSON array of four image xy points')
p.add_argument('--output',required=True,type=pathlib.Path)
a=p.parse_args()
im=cv2.imread(str(a.image))
if im is None:raise ValueError('Cannot read camera image')
im=cv2.rotate(im,cv2.ROTATE_180)
source=np.array(json.loads(a.calibration),dtype=np.float32)
target=np.array(json.loads(a.target),dtype=np.float32)
def quad(v):
 if v.shape!=(4,2) or not np.isfinite(v).all():raise ValueError('Need four finite xy points')
 crosses=[]
 for i in range(4):
  u=v[(i+1)%4]-v[i];w=v[(i+2)%4]-v[(i+1)%4];crosses.append(u[0]*w[1]-u[1]*w[0])
 if min(crosses)<=0:raise ValueError('Expected convex TL/TR/BR/BL order')
quad(source);quad(target)
unit=np.array([[0,0],[1,0],[1,1],[0,1]],dtype=np.float32)
H=cv2.getPerspectiveTransform(source,unit)
result=cv2.perspectiveTransform(target[None],H)[0]
if not np.isfinite(result).all() or result.min()<0 or result.max()>1:raise ValueError('Target falls outside projector footprint')
back=cv2.perspectiveTransform(result[None],np.linalg.inv(H))[0]
error=float(np.linalg.norm(back-target,axis=1).max())
scene={'name':'Camera-mapped rotating cube','color':'#42ddff','speed':0.45,
 'vertices':[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],
 'faces':[[0,3,2,1],[4,5,6,7],[0,1,5,4],[3,7,6,2],[0,4,7,3],[1,2,6,5]]}
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'scene.json').write_text(json.dumps({'scene':scene,'corners':result.flatten().tolist(),'guides':True},indent=2))
(a.output/'calibration.json').write_text(json.dumps({'image':str(a.image),'rotation':180,'projector_resolution':[1920,1080],'camera_quad':source.tolist(),'target_camera_quad':target.tolist(),'camera_to_projector_normalized':H.tolist(),'roundtrip_error_px':error,'assumptions':['same flat plane','factory white screen represents full app framebuffer','projector pose and system keystone unchanged','lens distortion not corrected']},indent=2))
for points,color in [(source,(0,255,255)),(target,(0,255,0))]:
 cv2.polylines(im,[points.astype(np.int32)],True,color,2)
 for i,xy in enumerate(points):cv2.putText(im,str(i+1),tuple(xy.astype(int)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
cv2.imwrite(str(a.output/'selection.jpg'),im)
print(json.dumps({'corners':result.flatten().tolist(),'roundtrip_error_px':error},indent=2))
