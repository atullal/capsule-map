"""Artwork-registered light choreography for the Crimson King face (1400px BGR).
Light follows the printed eyes, teeth, cheeks and mouth; the drawing itself is not moved.
"""
import cv2,numpy as np
N=1400;TAU=2*np.pi;LOOP=28.8;BEAT=.6
S={}
def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def rgb(r,g,b):return np.float32([b,g,r])
def setup(reference,alpha):
 global S
 ref=cv2.resize(cv2.imread(str(reference)),(N,N));flat=cv2.bilateralFilter(ref,9,55,9).astype(np.float32)/255
 hsv=cv2.cvtColor(flat,cv2.COLOR_BGR2HSV);hsv[:,:,1]=np.clip(hsv[:,:,1]*1.25,0,1);hsv[:,:,2]=np.clip(hsv[:,:,2]*1.3,0,1);base=cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
 yy,xx=np.mgrid[:N,:N].astype(np.float32);x=xx*1600/N;y=yy*1600/N
 lum=cv2.cvtColor(flat,cv2.COLOR_BGR2GRAY);reflect=smooth((lum-.12)/.38)
 def polygon(points):
  mask=np.zeros((N,N),np.uint8);cv2.fillPoly(mask,[np.int32(np.array(points)*N/1600)],255);return cv2.GaussianBlur(mask.astype(np.float32)/255,(0,0),2)
 eyes=polygon([(62,397),(166,262),(355,175),(562,156),(643,244),(667,281),(587,350),(360,416),(118,420)])+polygon([(1078,217),(1170,145),(1330,125),(1470,192),(1579,359),(1512,408),(1318,405),(1150,359)])
 white=eyes*smooth((lum-.43)/.32)
 mouth=polygon([(660,787),(966,748),(1110,786),(1230,920),(1222,1145),(1220,1400),(1118,1500),(805,1518),(547,1418),(510,1190),(528,980)])
 toothbox=(((y>810)&(y<990))|((y>1308)&(y<1450)))& (x>540)&(x<1210)
 teeth=mouth*toothbox*smooth((lum-.48)/.3)
 edges=cv2.Canny(cv2.GaussianBlur(ref,(0,0),2),55,125);edges=cv2.GaussianBlur(edges.astype(np.float32)/255,(0,0),1.2)
 mouthr=np.sqrt(((x-873)/1.05)**2+((y-1175)/1.3)**2)
 eye_r=[np.hypot(x-231,y-341),np.hypot(x-1170,y-327)]
 cheek=np.exp(-(((x-294)/230)**2+((y-591)/170)**2))+np.exp(-(((x-1420)/210)**2+((y-563)/190)**2))
 angle=np.arctan2(y-800,x-800)/TAU;radius=np.hypot(x-800,y-800)
 S=dict(base=base,x=x,y=y,reflect=reflect,eyes=white,mouth=mouth,teeth=teeth,edges=edges,mouthr=mouthr,eye_r=eye_r,cheek=cheek,angle=angle,radius=radius,alpha=alpha)
def frame_light(t):
 t=t%LOOP;u=t/LOOP;beat=t/BEAT;x=S['x'];y=S['y'];r=S['radius']
 pulse=(.5+.5*np.cos(TAU*beat))**3
 breathe=.5+.5*np.sin(TAU*4*u)
 base=S['base']*(.28+.16*breathe+.1*np.sin(x/210-y/320+TAU*3*u))[...,None]
 chapter=int(t//7.2);local=t%7.2
 eye_gain=.30+.22*breathe+.28*pulse
 eyes=S['eyes']*(eye_gain+.32*np.exp(-((x-(beat%4)/4*1750)/135)**2))
 base+=eyes[...,None]*rgb(.62,.90,1)
 # Iris coronas follow the eye boundaries; black pupils remain black.
 for er in S['eye_r']:
  corona=np.exp(-((er-(142+10*np.sin(TAU*beat/4)))/19)**2)*S['eyes']
  base+=corona[...,None]*rgb(.28,.65,1)*(.45+.3*pulse)
 glint=(.5+.5*np.cos(TAU*(x/680-beat/8)))**12
 base+=S['teeth'][...,None]*(.32+.63*glint)[...,None]*rgb(1,.86,.56)
 base+=S['cheek'][...,None]*(.12+.25*breathe)*rgb(1,.22,.12)
 wave=(.5+.5*np.cos(TAU*(S['mouthr']/160-beat/4)))**5
 base+=S['mouth'][...,None]*wave[...,None]*rgb(.42,.10,.23)*(.3+.5*(chapter==2))
 # A travelling luminous contour follows the face's existing linework.
 contour=(.5+.5*np.cos(TAU*(S['angle']*3-r/1500-6*u)))**14
 base+=S['edges'][...,None]*(.25+.75*contour)[...,None]*rgb(1,.42,.24)
 if chapter==1:
  vapor=(.5+.5*np.sin(x/180+y/240-TAU*beat/8))**2
  base+=vapor[...,None]*S['reflect'][...,None]*rgb(.06,.09,.2)*.4
 elif chapter==2:
  shock=np.exp(-((S['mouthr']-(local%2.4)*440)/65)**2)
  base+=shock[...,None]*S['reflect'][...,None]*rgb(1,.2,.08)*.3
 elif chapter==3:
  orbit=(.5+.5*np.cos(TAU*(S['angle']-local/3.6)))**10
  base+=orbit[...,None]*S['edges'][...,None]*rgb(1,.8,.45)*.65
 fade=smooth(t/1.3)*(1-smooth((t-(LOOP-1.7))/1.7))
 return np.clip(base,0,1)*S['reflect'][...,None]*S['alpha'][...,None]*fade
