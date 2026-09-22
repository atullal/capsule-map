package dev.atul.capsulemap;

import android.app.Activity;
import android.os.Bundle;
import android.content.*;
import android.graphics.*;
import android.view.*;
import android.widget.*;
import android.media.MediaPlayer;
import java.io.File;
import java.io.IOException;

/** Native-size playback of prewarped assets; never applies a second mapping. */
public final class MediaActivity extends Activity {
    static MediaActivity live;
    static volatile String currentFile="", playback="idle", error="";
    VideoView video; Bitmap bitmap;
    int position, generation; String name;
    final android.os.Handler timer=new android.os.Handler(android.os.Looper.getMainLooper());
    boolean resumed,holdOnResume;
    static File resolve(Context c,String name) throws IOException {
        File root=c.getExternalFilesDir(null);
        if(root==null||name==null||!name.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}"))throw new IOException("Invalid media filename");
        File file=new File(root,name);
        if(!file.getCanonicalPath().startsWith(root.getCanonicalPath()+"/")||!file.isFile()||file.length()==0)throw new IOException("Media file missing or empty");
        if(!name.endsWith(".mp4")&&!name.endsWith(".png"))throw new IOException("Use an MP4 or PNG file");
        if(name.endsWith(".png")){
            BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeFile(file.getPath(),options);
            if(options.outWidth<1||options.outHeight<1||options.outWidth>4096||options.outHeight>4096)throw new IOException("PNG dimensions invalid or above 4096 pixels");
        }
        return file;
    }
    public void onCreate(Bundle b){super.onCreate(b);live=this;getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);getWindow().getDecorView().setSystemUiVisibility(5894|1024|512);name=getIntent().getStringExtra("file");position=b==null?Math.max(0,getIntent().getIntExtra("seekMs",0)):b.getInt("position",0);}
    public void onNewIntent(Intent i){super.onNewIntent(i);if(i.getBooleanExtra("captureHold",false)){holdOnResume=true;return;}if(i.getBooleanExtra("resumeOnly",false))return;setIntent(i);name=i.getStringExtra("file");position=Math.max(0,i.getIntExtra("seekMs",0));if(resumed)show();}
    void holdProjection(){holdProjection(0);}
    void holdProjection(final int attempt){
        final Bitmap held=Bitmap.createBitmap(1920,1080,Bitmap.Config.ARGB_8888);
        CaptureGuardService.status="copying";
        if(video!=null&&video.getHolder().getSurface().isValid()){
            try{PixelCopy.request(video.getHolder().getSurface(),held,new PixelCopy.OnPixelCopyFinishedListener(){public void onPixelCopyFinished(int result){
                if(!CaptureGuardService.status.equals("copying")){held.recycle();return;}
                if(result==PixelCopy.SUCCESS)CaptureGuardService.hold(MediaActivity.this,held,name);
                else{held.recycle();if(attempt<12&&resumed){timer.postDelayed(new Runnable(){public void run(){if(CaptureGuardService.status.equals("copying"))holdProjection(attempt+1);}},100);}else CaptureGuardService.status="error: Cannot copy video frame ("+result+")";}
            }},timer);}catch(Exception e){held.recycle();CaptureGuardService.status="error: "+e.getMessage();}
        }else if(bitmap!=null){Canvas canvas=new Canvas(held);canvas.drawColor(Color.BLACK);canvas.drawBitmap(bitmap,null,new Rect(0,0,1920,1080),new Paint(Paint.FILTER_BITMAP_FLAG));CaptureGuardService.hold(this,held,name);}
        else{held.recycle();CaptureGuardService.status="error: No projection ready to capture";}
    }
    protected void onResume(){super.onResume();resumed=true;if(holdOnResume){holdOnResume=false;if(video!=null)video.start();holdProjection();}else show();}
    protected void onPause(){resumed=false;if(video!=null){position=video.getCurrentPosition();video.pause();}if(!playback.equals("error"))playback="paused";super.onPause();}
    protected void onSaveInstanceState(Bundle b){b.putInt("position",video==null?position:video.getCurrentPosition());super.onSaveInstanceState(b);}
    void release(){generation++;timer.removeCallbacksAndMessages(null);if(video!=null){video.stopPlayback();video=null;}setContentView(new View(this));if(bitmap!=null){bitmap.recycle();bitmap=null;}}
    void fail(String message){release();playback="error";error=message;LinearLayout box=new LinearLayout(this);box.setOrientation(1);box.setPadding(60,60,60,60);box.setBackgroundColor(Color.BLACK);TextView text=new TextView(this);text.setTextColor(Color.WHITE);text.setTextSize(24);text.setText("Playback unavailable\n"+message);box.addView(text);Button retry=new Button(this);retry.setText("Retry");retry.setOnClickListener(new View.OnClickListener(){public void onClick(View v){show();}});box.addView(retry);Button back=new Button(this);back.setText("Return to controller");back.setOnClickListener(new View.OnClickListener(){public void onClick(View v){finish();}});box.addView(back);setContentView(box);retry.requestFocus();}
    void show(){
        release();currentFile=name==null?"":name;error="";playback="loading";
        try {
            File file=resolve(this,name);final int token=generation;
            if(name.endsWith(".mp4")){
                video=new VideoView(this){protected void onMeasure(int w,int h){setMeasuredDimension(MeasureSpec.getSize(w),MeasureSpec.getSize(h));}};
                setContentView(video);
                video.setOnErrorListener(new MediaPlayer.OnErrorListener(){public boolean onError(MediaPlayer m,int what,int extra){if(token==generation)fail("Cannot decode "+name+" ("+what+"/"+extra+")");return true;}});
                video.setOnPreparedListener(new MediaPlayer.OnPreparedListener(){public void onPrepared(MediaPlayer m){if(token!=generation||!resumed)return;m.setLooping(true);m.setVolume(0,0);if(position>0)m.seekTo(position%Math.max(1,m.getDuration()));video.start();playback="playing";}});
                video.setVideoPath(file.getAbsolutePath());
                timer.postDelayed(new Runnable(){public void run(){if(token==generation&&resumed&&playback.equals("loading"))fail("Video did not become ready. Retry or choose another file.");}},15000);
            }else{
                bitmap=BitmapFactory.decodeFile(file.getAbsolutePath());if(bitmap==null)throw new IOException("Cannot decode PNG");final Bitmap image=bitmap;
                setContentView(new View(this){final Paint paint=new Paint(Paint.FILTER_BITMAP_FLAG);protected void onDraw(Canvas c){c.drawColor(Color.BLACK);c.drawBitmap(image,null,new Rect(0,0,getWidth(),getHeight()),paint);}});playback="showing";
            }
        }catch(Exception e){fail(e.getMessage());}
    }
    public void onDestroy(){if(live==this)live=null;release();if(currentFile.equals(name)){playback="idle";currentFile="";}super.onDestroy();}
}
