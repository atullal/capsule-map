package dev.atul.capsulemap;

import android.app.Service;
import android.content.Intent;
import android.graphics.*;
import android.os.*;
import android.provider.Settings;
import android.view.*;

/** Holds the projected frame above the stock camera UI during a bounded capture. */
public final class CaptureGuardService extends Service {
    static volatile String status="idle";
    private final Handler handler=new Handler(Looper.getMainLooper());
    private WindowManager windows;private View guard;private Bitmap bitmap;
    private String resumeFile;
    private String patternName;
    private final Runnable watchdog=new Runnable(){public void run(){Intent restore=new Intent(CaptureGuardService.this,resumeFile==null?MainActivity.class:MediaActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);if(resumeFile!=null)restore.putExtra("file",resumeFile);startActivity(restore);handler.postDelayed(new Runnable(){public void run(){stopSelf();}},1000);}};
    private void armWatchdog(){handler.removeCallbacks(watchdog);handler.postDelayed(watchdog,14000);}
    private void acknowledge(){if(patternName==null)return;try{java.io.File f=new java.io.File(getExternalFilesDir(null),"capture-pattern-ready");java.io.File tmp=new java.io.File(f.getPath()+".tmp");java.io.FileOutputStream out=new java.io.FileOutputStream(tmp);out.write(patternName.getBytes("UTF-8"));out.close();tmp.renameTo(f);}catch(Exception e){status="error: Pattern acknowledgement failed";}}
    private static Bitmap pendingFrame;
    static void hold(android.app.Activity activity,Bitmap frame,String file){
        if(pendingFrame!=null)pendingFrame.recycle();pendingFrame=frame;status="starting";
        Intent intent=new Intent(activity,CaptureGuardService.class);if(file!=null)intent.putExtra("resumeFile",file);activity.startService(intent);
    }
    public IBinder onBind(Intent intent){return null;}
    public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&intent.hasExtra("pattern")){
            try{String next=intent.getStringExtra("pattern");Bitmap generated=CalibrationPattern.gray(next);patternName=next;
                if(guard!=null){Bitmap previous=bitmap;bitmap=generated;status="starting";guard.invalidate();if(previous!=null)previous.recycle();armWatchdog();return START_NOT_STICKY;}
                pendingFrame=generated;
            }catch(Exception e){status="error: "+e.getMessage();stopSelf();return START_NOT_STICKY;}
        }else if(guard!=null)return START_NOT_STICKY;
        if(intent!=null&&intent.getBooleanExtra("prepare",false)){
            status="copying";
            if(MediaActivity.live!=null&&MediaActivity.live.resumed)MediaActivity.live.holdProjection();
            else if(MainActivity.live!=null&&MainActivity.live.map.active){Bitmap held=Bitmap.createBitmap(1920,1080,Bitmap.Config.ARGB_8888);MainActivity.live.map.draw(new Canvas(held));hold(MainActivity.live,held,null);}
            else{status="error: Open a projection before capturing";stopSelf();}
            handler.postDelayed(new Runnable(){public void run(){if(guard==null)stopSelf();}},3500);
            return START_NOT_STICKY;
        }
        try{
            if(!Settings.canDrawOverlays(this))throw new Exception("Overlay permission missing");
            resumeFile=intent==null?null:intent.getStringExtra("resumeFile");
            bitmap=pendingFrame;pendingFrame=null;
            if(bitmap==null||bitmap.getWidth()!=1920||bitmap.getHeight()!=1080)throw new Exception("No native hold frame prepared");
            guard=new View(this){private final Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG);protected void onDraw(Canvas c){c.drawColor(Color.BLACK);if(bitmap!=null)c.drawBitmap(bitmap,null,new Rect(0,0,getWidth(),getHeight()),paint);status="holding";acknowledge();}};
            guard.setSystemUiVisibility(5894|1024|512);
            windows=(WindowManager)getSystemService(WINDOW_SERVICE);
            WindowManager.LayoutParams params=new WindowManager.LayoutParams(-1,-1,WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN|WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,PixelFormat.OPAQUE);
            params.alpha=1f;params.gravity=Gravity.TOP|Gravity.LEFT;status="starting";windows.addView(guard,params);
            armWatchdog();
        }catch(Exception e){status="error: "+e.getMessage();stopSelf();}
        return START_NOT_STICKY;
    }
    public void onDestroy(){handler.removeCallbacksAndMessages(null);if(guard!=null&&windows!=null)windows.removeViewImmediate(guard);if(bitmap!=null)bitmap.recycle();guard=null;bitmap=null;if(!status.startsWith("error:"))status="idle";super.onDestroy();}
}
