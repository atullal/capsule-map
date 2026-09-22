package dev.atul.capsulemap;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.Manifest;
import android.content.pm.PackageManager;
import android.content.Context;
import android.graphics.*;
import android.hardware.camera2.*;
import android.net.wifi.WifiManager;
import android.view.*;

import org.json.*;
import java.io.*;
import java.net.*;
import java.util.*;

public final class MainActivity extends Activity {
  static MainActivity live;
  final Handler main = new Handler(Looper.getMainLooper());
  volatile Scene3D scene3d;
  volatile boolean meshMode;
  volatile String prompt = "ocean waves";
  volatile String cameraStatus = "Checking camera API…";
  volatile boolean guides = true;
  volatile float[] corners = {0.15f,0.15f,0.85f,0.15f,0.85f,0.85f,0.15f,0.85f};
  String pin; String ip = "unknown";
  MapView map;
  LocalHttp server;
  volatile boolean destroyed;
  String serverStatus="Starting";
  CameraDevice opened;
  @Override public void onCreate(Bundle b) { super.onCreate(b); live=this;getWindow().getDecorView().setSystemUiVisibility(5894|1024|512); pin=getPreferences(0).getString("pin",null); if(pin==null){pin=String.format(Locale.US,"%06d",new java.security.SecureRandom().nextInt(1000000));getPreferences(0).edit().putString("pin",pin).commit();} getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); map=new MapView(this); setContentView(map); map.setFocusableInTouchMode(true); map.requestFocus(); restoreState(); ip=localIp(); startServer(); checkCamera(); }
  @Override public void onNewIntent(android.content.Intent i){super.onNewIntent(i);if(i.getBooleanExtra("captureHold",false)){Bitmap held=Bitmap.createBitmap(1920,1080,Bitmap.Config.ARGB_8888);map.draw(new Canvas(held));CaptureGuardService.hold(this,held,null);}}
  @Override public void onDestroy(){if(live==this)live=null;destroyed=true;main.removeCallbacksAndMessages(null);try{if(server!=null)server.close(); if(opened!=null)opened.close();}catch(Exception ignored){}super.onDestroy();}
  String localIp(){ try {WifiManager w=(WifiManager)getApplicationContext().getSystemService(WIFI_SERVICE);int a=w.getConnectionInfo().getIpAddress();if(a!=0)return String.format(Locale.US,"%d.%d.%d.%d",a&255,a>>8&255,a>>16&255,a>>24&255);}catch(Exception ignored){} try{Enumeration<NetworkInterface> es=NetworkInterface.getNetworkInterfaces();while(es.hasMoreElements()){NetworkInterface ni=es.nextElement();for(InterfaceAddress ia:ni.getInterfaceAddresses()){InetAddress a=ia.getAddress();if(a instanceof Inet4Address&&!a.isLoopbackAddress()&&!a.isLinkLocalAddress())return a.getHostAddress();}}}catch(Exception ignored){}return "unknown";}
  void checkCamera(){try{CameraManager mgr=(CameraManager)getSystemService(Context.CAMERA_SERVICE); String[] ids=mgr.getCameraIdList();if(ids.length==0){cameraStatus="Camera2: 0 cameras. Internal sensor capture verified via Nebula factory bridge.";map.invalidate();return;}StringBuilder sb=new StringBuilder("Camera2 IDs: ");for(String id:ids){CameraCharacteristics c=mgr.getCameraCharacteristics(id);Integer face=c.get(CameraCharacteristics.LENS_FACING);sb.append(id).append(" (facing ").append(face).append(") ");}cameraStatus=sb.toString()+" • Opening first camera…";map.invalidate();if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.CAMERA},9);return;}tryOpen(ids[0]);}catch(Exception e){cameraStatus="Camera2 query failed: "+e.getClass().getSimpleName()+": "+e.getMessage();map.invalidate();}}
  @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants){super.onRequestPermissionsResult(request,permissions,grants);if(request==9){if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED)checkCamera();else{cameraStatus="Camera listed; CAMERA permission denied. Grant it to test opening.";map.invalidate();}}}
  void tryOpen(String id){try{CameraManager mgr=(CameraManager)getSystemService(Context.CAMERA_SERVICE);mgr.openCamera(id,new CameraDevice.StateCallback(){@Override public void onOpened(CameraDevice d){opened=d;cameraStatus="Camera2 ID "+id+" opened successfully; image stream untested. This may not be the calibration camera.";map.invalidate();d.close();opened=null;}@Override public void onDisconnected(CameraDevice d){cameraStatus="Camera "+id+" disconnected";map.invalidate();d.close();}@Override public void onError(CameraDevice d,int error){cameraStatus="Camera "+id+" open failed (code "+error+")";map.invalidate();d.close();}},main);}catch(Exception e){cameraStatus="Camera "+id+" open error: "+e.getClass().getSimpleName()+": "+e.getMessage();map.invalidate();}}
  void startServer(){try{server=new LocalHttp(8765,new LocalHttp.Router(){public String route(final String method,final String path,final String body) throws Exception {
    // Serialize complete state transactions with the renderer and activity lifecycle.
    final java.util.concurrent.FutureTask<String> task=new java.util.concurrent.FutureTask<String>(new java.util.concurrent.Callable<String>(){public String call() throws Exception {
      if(destroyed)throw new LocalHttp.Failure(503,"Controller stopped");
      return MainActivity.this.route(method,path,body);
    }});
    main.post(task);
    try{return task.get(8,java.util.concurrent.TimeUnit.SECONDS);}
    catch(java.util.concurrent.ExecutionException e){Throwable cause=e.getCause();if(cause instanceof Exception)throw (Exception)cause;throw e;}
    catch(java.util.concurrent.TimeoutException e){task.cancel(false);throw new LocalHttp.Failure(503,"Projector busy; check state before retrying");}
  }});serverStatus="Listening";}catch(IOException e){serverStatus="Controller unavailable: "+e.getMessage();}}
  String route(String method,String path,String body) throws Exception {
    if(path.equals("/")&&method.equals("GET"))return HTML;
    if(path.equals("/state")&&method.equals("GET")){
      JSONObject o=new JSONObject();o.put("prompt",prompt);o.put("corners",new JSONArray(corners));o.put("guides",guides);o.put("camera",cameraStatus);
      o.put("mode",(MediaActivity.playback.equals("playing")||MediaActivity.playback.equals("showing")||MediaActivity.playback.equals("loading")||MediaActivity.playback.equals("error"))?"media":meshMode?"mesh3d":"effects");
      o.put("captureGuard",CaptureGuardService.status);o.put("mappingMode",meshMode?"mesh3d":"effects");o.put("server",serverStatus);
      JSONObject media=new JSONObject();media.put("file",MediaActivity.currentFile);media.put("status",MediaActivity.playback);media.put("error",MediaActivity.error);o.put("media",media);
      if(!MediaActivity.currentFile.isEmpty()){JSONObject calibration=mediaMetadata(MediaActivity.currentFile);if(calibration!=null)o.put("calibration",calibration);}
      if(scene3d!=null)o.put("scene",scene3d.json);return o.toString();
    }
    if(path.equals("/media")&&method.equals("GET")){
      JSONArray files=new JSONArray();File root=getExternalFilesDir(null);File[] list=root==null?null:root.listFiles();
      if(list!=null){Arrays.sort(list);for(File file:list)if(file.getName().endsWith(".mp4"))try{MediaActivity.resolve(this,file.getName());JSONObject f=new JSONObject();f.put("name",file.getName());f.put("bytes",file.length());files.put(f);}catch(IOException ignored){}}
      return new JSONObject().put("files",files).toString();
    }
    if(!Arrays.asList("/update","/scene","/media").contains(path))throw new LocalHttp.Failure(404,"Not found");
    if(!method.equals("POST"))throw new LocalHttp.Failure(405,"Use POST");
    JSONObject o=new JSONObject(body);
    if(!pin.equals(o.optString("pin")))throw new LocalHttp.Failure(403,"Wrong PIN");
    if(path.equals("/media")){
      String action=o.getString("action");
      if(action.equals("play")){
        String file=o.getString("file");try{MediaActivity.resolve(this,file);}catch(IOException e){throw new LocalHttp.Failure(400,e.getMessage());}
        startActivity(new android.content.Intent(this,MediaActivity.class).putExtra("file",file));
      }else if(action.equals("stop")){foreground();}else throw new LocalHttp.Failure(400,"Use play or stop");
    }else if(path.equals("/update")){
      String nextPrompt=prompt;boolean nextGuides=guides;float[] nextCorners=corners;
      if(o.has("prompt")){if(!(o.get("prompt") instanceof String))throw new JSONException("Prompt must be text");nextPrompt=o.getString("prompt");if(nextPrompt.length()>180)throw new JSONException("Prompt exceeds 180 characters");}
      if(o.has("guides")){if(!(o.get("guides") instanceof Boolean))throw new JSONException("Guides must be boolean");nextGuides=o.getBoolean("guides");}
      if(o.has("corners"))nextCorners=validatedCorners(o.getJSONArray("corners"));
      prompt=nextPrompt;guides=nextGuides;corners=nextCorners;if(o.has("prompt"))meshMode=false;persistState();foreground();map.invalidate();
    }else{
      Scene3D next=new Scene3D(o.getJSONObject("scene"));float[] nextCorners=validatedCorners(o.getJSONArray("corners"));
      boolean nextGuides=o.has("guides")?o.getBoolean("guides"):false;
      scene3d=next;corners=nextCorners;meshMode=true;guides=nextGuides;persistState();foreground();map.invalidate();
    }
    return "{\"ok\":true}";
  }
  JSONObject mediaMetadata(String name){
    try{File root=getExternalFilesDir(null);if(root==null||!name.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}"))return null;File f=new File(root,name+".json");if(!f.isFile()||f.length()>65536)return null;ByteArrayOutputStream bytes=new ByteArrayOutputStream();try(InputStream input=new FileInputStream(f)){byte[] buffer=new byte[4096];for(int n;(n=input.read(buffer))!=-1;){if(bytes.size()+n>65536)return null;bytes.write(buffer,0,n);}}return new JSONObject(new String(bytes.toByteArray(),java.nio.charset.StandardCharsets.UTF_8));}catch(Exception e){return null;}
  }
  void foreground(){startActivity(new android.content.Intent(this,MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP|android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP));}
  static float[] validatedCorners(JSONArray a) throws JSONException {
    if(a.length()!=8)throw new JSONException("Need four xy corners");
    float[] out=new float[8];
    for(int i=0;i<8;i++){double v=a.getDouble(i);if(Double.isNaN(v)||Double.isInfinite(v)||v<0||v>1)throw new JSONException("Corners must be finite in [0,1]");out[i]=(float)v;}
    double area=0;
    for(int i=0;i<4;i++){int j=(i+1)%4,k=(i+2)%4;
      float cross=(out[2*j]-out[2*i])*(out[2*k+1]-out[2*j+1])-(out[2*j+1]-out[2*i+1])*(out[2*k]-out[2*j]);
      if(cross<=0.0001f)throw new JSONException("Corners must form a clockwise convex quad: TL,TR,BR,BL");
      area+=out[2*i]*out[2*j+1]-out[2*j]*out[2*i+1];
    }
    if(area<.005)throw new JSONException("Mapping area too small");return out;
  }
  void persistState(){try {JSONObject o=new JSONObject();o.put("prompt",prompt);o.put("corners",new JSONArray(corners));o.put("guides",guides);o.put("meshMode",meshMode);if(scene3d!=null)o.put("scene",scene3d.json);getPreferences(0).edit().putString("mapping",o.toString()).apply();}catch(Exception ignored){}}
  void restoreState(){try {String data=getPreferences(0).getString("mapping",null);if(data==null)return;JSONObject o=new JSONObject(data);corners=validatedCorners(o.getJSONArray("corners"));prompt=o.optString("prompt","ocean waves");guides=o.optBoolean("guides",true);if(o.has("scene"))scene3d=new Scene3D(o.getJSONObject("scene"));meshMode=o.optBoolean("meshMode",false)&&scene3d!=null;}catch(Exception ignored){}}
  @Override protected void onResume(){super.onResume();if(map!=null){map.active=true;map.invalidate();}ip=localIp();}
  @Override protected void onPause(){if(map!=null)map.active=false;super.onPause();}
  final class MapView extends View {
   boolean active=true;
   Paint p=new Paint(3); long start=android.os.SystemClock.uptimeMillis(); MapView(Context c){super(c);setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
   @Override protected void onDraw(Canvas canvas){int w=getWidth(),h=getHeight();if(!meshMode&&prompt.equals("calibration markers")){CalibrationPattern.draw(canvas,w,h,p);if(active)postInvalidateDelayed(100);return;}canvas.drawColor(Color.BLACK);float[] c=corners;float[] dst={c[0]*w,c[1]*h,c[2]*w,c[3]*h,c[4]*w,c[5]*h,c[6]*w,c[7]*h};Path mask=new Path();mask.moveTo(dst[0],dst[1]);for(int i=2;i<8;i+=2)mask.lineTo(dst[i],dst[i+1]);mask.close();Matrix m=new Matrix();m.setPolyToPoly(new float[]{0,0,1000,0,1000,600,0,600},0,dst,0,4);canvas.save();canvas.clipPath(mask);canvas.concat(m);float t=(android.os.SystemClock.uptimeMillis()-start)/1000f;String s=prompt.toLowerCase(Locale.US);boolean wave=s.contains("wave")||s.contains("ocean")||s.contains("water");boolean stars=s.contains("star")||s.contains("space")||s.contains("galaxy");boolean grid=s.contains("grid")||s.contains("matrix")||s.contains("cyber");p.setStyle(Paint.Style.FILL);p.setColor(wave?Color.rgb(1,17,43):stars?Color.rgb(12,5,35):grid?Color.rgb(2,19,16):Color.rgb(27,7,35));canvas.drawRect(0,0,1000,600,p);
    if(meshMode&&scene3d!=null){scene3d.draw(canvas,p,t);}
    else if(wave){for(int j=0;j<18;j++){Path path=new Path();for(int x=0;x<=1000;x+=10){float y=90+j*28+(float)Math.sin(x*.012+t*1.4+j*.42)*22;if(x==0)path.moveTo(x,y);else path.lineTo(x,y);}p.setColor(Color.HSVToColor(new float[]{190+3*j,.75f,.3f+.03f*j}));p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);canvas.drawPath(path,p);}}
    else if(stars){for(int i=0;i<130;i++){float x=(i*7919%997),y=(i*5701%593),r=1+(i%4);p.setColor(Color.argb(80+(int)(175*Math.abs(Math.sin(t*1.8+i))),170+i%85,170+i%65,255));p.setStyle(Paint.Style.FILL);canvas.drawCircle(x,y,r,p);}}
    else if(grid){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2);p.setColor(Color.rgb(36,245,176));for(int i=0;i<22;i++){float x=(i*54+t*24)%1100;canvas.drawLine(x,0,x-100,600,p);}for(int j=0;j<14;j++){float y=(j*50+t*18)%650;canvas.drawLine(0,y,1000,y,p);}}
    else{for(int j=0;j<16;j++){float x=500+(float)Math.sin(t*.7+j*2.4)*(50+j*22),y=300+(float)Math.cos(t*.8+j*2.4)*(30+j*15);p.setStyle(Paint.Style.FILL);p.setColor(Color.HSVToColor(new float[]{(j*24+(int)(t*12))%360,.72f,.85f}));canvas.drawCircle(x,y,12+j*2,p);}}canvas.restore();
    if(guides){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(3);p.setColor(Color.WHITE);canvas.drawPath(mask,p);p.setStyle(Paint.Style.FILL);for(int i=0;i<8;i+=2){p.setColor(Color.YELLOW);canvas.drawCircle(dst[i],dst[i+1],9,p);}p.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));p.setTextSize(Math.max(16,h*.026f));p.setColor(Color.WHITE);canvas.drawText("CAPSULE MAP  •  "+ip+":8765  •  PIN "+pin,25,35,p);p.setTypeface(Typeface.DEFAULT);p.setTextSize(Math.max(13,h*.021f));String diagnostic=serverStatus.equals("Listening")?cameraStatus:serverStatus;canvas.drawText(diagnostic.length()>110?diagnostic.substring(0,110):diagnostic,25,h-24,p);}if(active)postInvalidateDelayed(33);
   }
   @Override public boolean onKeyDown(int k,android.view.KeyEvent e){if(k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER){guides=!guides;persistState();invalidate();return true;}return super.onKeyDown(k,e);}
  }
  static final String HTML="\n<!doctype html><html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Capsule Map</title><style>body{margin:0;background:#10131b;color:#eef2fa;font:16px system-ui;padding:22px;max-width:650px;margin:auto}h1{font-size:28px}p{color:#a9b2c4;line-height:1.5}label{display:block;margin:20px 0 8px}textarea,input,button{box-sizing:border-box;font:inherit}textarea,input{background:#232936;color:white;border:1px solid #526079;border-radius:9px;padding:12px;width:100%}button{background:#638bff;border:0;color:#10131b;border-radius:9px;padding:13px 18px;font-weight:700;margin:10px 8px 10px 0}canvas{width:100%;touch-action:none;border-radius:12px;background:#050507;border:1px solid #526079}small{color:#9aa9bf}</style></head><body><h1>Capsule Map</h1><p>Connect your phone and projector to the same Wi-Fi. Enter the PIN shown on the projection. Drag the four corners below to match your physical area.</p><label>Projector PIN</label><input id=\"pin\" inputmode=\"numeric\" maxlength=\"6\" placeholder=\"6-digit PIN\"><label>Album animation</label><select id=\"mediaFiles\" style=\"width:100%;padding:12px\"></select><div><button id=\"playMedia\">Play album</button><button id=\"stopMedia\">Return to effects</button></div><p id=\"playback\" aria-live=\"polite\">Connecting\u2026</p><p id=\"calibration\"></p><label>Effect prompt</label><textarea id=\"prompt\" rows=\"3\">ocean waves</textarea><p>Built-in effects respond to \u201cocean / waves\u201d, \u201cstars / galaxy\u201d, and \u201cgrid / cyber\u201d. Other prompts use color particles. This prototype does not call an AI model.</p><label>Mapping corners</label><canvas id=\"cv\" width=\"600\" height=\"360\"></canvas><div><button id=\"send\">Project</button><button id=\"guides\">Hide / show guides</button><button id=\"reset\">Reset corners</button></div><p id=\"msg\"></p><small id=\"camera\"></small><script>\nlet c=[.15,.15,.85,.15,.85,.85,.15,.85],g=true,cv=document.getElementById('cv'),ctx=cv.getContext('2d'),active=-1;document.getElementById('pin').value=localStorage.getItem('capsulePin')||'';function draw(){ctx.fillStyle='#060b15';ctx.fillRect(0,0,600,360);ctx.beginPath();for(let i=0;i<4;i++){let x=c[2*i]*600,y=c[2*i+1]*360;if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y)}ctx.closePath();ctx.fillStyle='#3452a7';ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2;ctx.stroke();for(let i=0;i<4;i++){ctx.beginPath();ctx.arc(c[2*i]*600,c[2*i+1]*360,11,0,7);ctx.fillStyle='#ffd859';ctx.fill();ctx.fillStyle='#111';ctx.font='bold 13px system-ui';ctx.fillText(''+(i+1),c[2*i]*600-4,c[2*i+1]*360+5)}}draw();function pos(e){let r=cv.getBoundingClientRect();return [(e.clientX-r.left)*600/r.width,(e.clientY-r.top)*360/r.height]}cv.onpointerdown=e=>{let [x,y]=pos(e),d=1e9;for(let i=0;i<4;i++){let z=Math.hypot(x-c[2*i]*600,y-c[2*i+1]*360);if(z<d){d=z;active=i}}cv.setPointerCapture(e.pointerId)};cv.onpointermove=e=>{if(active<0)return;let [x,y]=pos(e);c[2*active]=Math.max(0,Math.min(1,x/600));c[2*active+1]=Math.max(0,Math.min(1,y/360));draw()};cv.onpointerup=()=>active=-1;cv.onpointercancel=()=>active=-1;async function request(path,data){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);try{let r=await fetch(path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,signal:controller.signal});let v=await r.json();if(!r.ok)throw Error(v.error||`HTTP ${r.status}`);return v}finally{clearTimeout(timer)}}\nfunction credentials(){let pin=document.getElementById('pin').value;localStorage.setItem('capsulePin',pin);return pin}\nasync function send(extra){try{await request('/update',Object.assign({pin:credentials()},extra||{prompt:document.getElementById('prompt').value,corners:c,guides:g}));document.getElementById('msg').textContent='Projection updated.';await status()}catch(e){document.getElementById('msg').textContent=e.message}}\nasync function status(){try{let v=await request('/state');document.getElementById('playback').textContent=v.mode==='media'?`${v.media.file}: ${v.media.status}${v.media.error?' \u2014 '+v.media.error:''}`:`Connected \u00b7 ${v.mode}`;document.getElementById('calibration').textContent=v.calibration?`Calibration: ${(v.calibration.beam_coverage_fraction*100).toFixed(1)}% coverage \u00b7 ${v.calibration.held_out_rms_px.toFixed(2)} px held-out error. Recalibrate after moving the projector or artwork.`:'This media has no attached calibration report.';return v}catch(e){document.getElementById('playback').textContent='Disconnected \u2014 check projector Wi-Fi. '+e.message}}\nasync function media(action){try{await request('/media',{pin:credentials(),action,file:document.getElementById('mediaFiles').value});await status()}catch(e){document.getElementById('msg').textContent=e.message}}\ndocument.getElementById('playMedia').onclick=()=>media('play');document.getElementById('stopMedia').onclick=()=>media('stop');\nrequest('/media').then(v=>{let list=document.getElementById('mediaFiles');for(let file of v.files){let option=document.createElement('option');option.value=file.name;option.textContent=file.name;list.appendChild(option)}document.getElementById('playMedia').disabled=!v.files.length}).catch(e=>document.getElementById('msg').textContent=e.message);\nsetInterval(status,3000);\ndocument.getElementById('send').onclick=()=>send();document.getElementById('guides').onclick=()=>{g=!g;send({guides:g})};document.getElementById('reset').onclick=()=>{c=[.15,.15,.85,.15,.85,.85,.15,.85];draw();send({corners:c})};status().then(v=>{if(!v)return;c=v.corners;g=v.guides;document.getElementById('prompt').value=v.prompt;document.getElementById('camera').textContent='Camera diagnostic: '+v.camera;draw()});</script></body></html>\n";
}
