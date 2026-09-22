"""Reuse the existing Life & Love artwork-space animation with the Nebula sensor map."""
import sys,pathlib,os,multiprocessing,cv2,numpy as np
import argparse,json,hashlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--run",required=True,type=pathlib.Path);p.add_argument("--source",type=pathlib.Path,default=(pathlib.Path(__file__).resolve().parents[2]/'vendor/projection-mapping'));p.add_argument("--sheet",action="store_true");a=p.parse_args();RUN=a.run.resolve()
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCE=a.source.resolve()
sys.path.insert(0,str(SOURCE))
FPS=24
OUT=RUN/'frames'

def setup():
    global anim
    cv2.setNumThreads(1)
    import animate as anim
    import render
    anim.CALIB=str(RUN/'calib');render.CALIB=anim.CALIB
    anim.setup()

def frame(i):
    light=(anim.frame_light(i/FPS)*255+.5).astype(np.uint8)
    if not cv2.imwrite(str(OUT/f'f{i:04d}.jpg'),anim.S['warp'].full(light),[cv2.IMWRITE_JPEG_QUALITY,95]):raise RuntimeError('Could not save frame '+str(i))
    return i

if __name__=='__main__':
    metrics=json.loads((RUN/'calib/metrics.json').read_text())
    digest=hashlib.sha256((RUN/'calib/render_map.npz').read_bytes()).hexdigest()
    if digest!=metrics.get('render_map_sha256'):raise RuntimeError('Calibration lookup changed; recalibrate')
    if not a.sheet:
        verification=metrics.get('verification',{})
        photo=RUN/verification.get('photo','missing-verification')
        if metrics['status']!='visually_verified' or not photo.is_file() or hashlib.sha256(photo.read_bytes()).hexdigest()!=verification.get('sha256'):raise RuntimeError('Project and inspect the edge test, then record visual verification before rendering')
    OUT.mkdir(parents=True,exist_ok=True)
    if '--sheet' in sys.argv:
        setup();times=[0,1,3,5,7,9,11,13,15.99]
        tiles=[]
        for t in times:
            tile=cv2.resize((anim.frame_light(t)*255).astype(np.uint8),(420,420));cv2.putText(tile,f'{t:.2f}s',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.8,(255,255,255),2);tiles.append(tile)
        cv2.imwrite(str(RUN/'contact-sheet.jpg'),np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,9,3)]))
    else:
        (RUN/'render.json').unlink(missing_ok=True)
        with multiprocessing.Pool(4,initializer=setup) as pool:
            count=0
            for _ in pool.imap_unordered(frame,range(16*FPS),chunksize=4):
                count+=1
                if count%48==0:print(f'rendered {count}/{16*FPS}',flush=True)

        (RUN/'render.json').write_text(json.dumps({'schema':1,'render_map_sha256':digest,'fps':FPS,'frames':16*FPS,'duration_seconds':16,'frames_per_beat':FPS*60/90,'size':[1920,1080]},indent=2))
