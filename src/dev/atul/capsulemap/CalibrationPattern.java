package dev.atul.capsulemap;
import android.graphics.*;
final class CalibrationPattern {
  static final String[] TAGS={"000000010110001010000110000100000000","000000000000011110010010010100000000","000000000110000110000100011010000000","000000010010010010001000001100000000","000000001010001000010010011100000000","000000001110010010011000011010000000","000000010010011100000100011100000000","000000011000001000011110000100000000","000000011110011100011010010100000000","000000011000011110001010001100000000","000000011110010010010010000010000000","000000000010000010010100001110000000","000000000000011100010110001110000000","000000000100010100000000011110000000","000000000100001000010110000010000000"};
  /** Exact STEP=4 Gray code matching projection-mapping/calibrate.py. */
  static Bitmap gray(String name){
    if(name==null||!(name.equals("white")||name.equals("black")||name.matches("[xy]0[0-8][pn]")))throw new IllegalArgumentException("Invalid calibration pattern");
    Bitmap image=Bitmap.createBitmap(1920,1080,Bitmap.Config.ARGB_8888);
    Canvas c=new Canvas(image);c.drawColor(name.equals("white")?Color.WHITE:Color.BLACK);
    if(name.equals("white")||name.equals("black"))return image;
    Paint p=new Paint();p.setColor(Color.WHITE);boolean x=name.charAt(0)=='x';int bit=name.charAt(2)-'0';boolean inverse=name.charAt(3)=='n';
    int limit=x?1920:1080;
    for(int pos=0;pos<limit;pos+=4){int cell=pos/4;boolean lit=(((cell^(cell>>1))>>bit)&1)!=0;if(lit!=inverse){if(x)c.drawRect(pos,0,Math.min(pos+4,1920),1080,p);else c.drawRect(0,pos,1920,Math.min(pos+4,1080),p);}}
    return image;
  }
  static void draw(Canvas canvas,int w,int h,Paint p){
    canvas.drawColor(Color.BLACK);p.setStyle(Paint.Style.FILL);
    float cell=Math.min(w/80f,h/48f);
    for(int id=0;id<TAGS.length;id++){
      float cx=w*((id%5)+1)/6f,cy=h*((id/5)+1)/4f;
      float x=cx-4*cell,y=cy-4*cell;
      p.setColor(Color.WHITE);canvas.drawRect(x,y,x+8*cell,y+8*cell,p);
      for(int row=0;row<6;row++)for(int col=0;col<6;col++){
        p.setColor(TAGS[id].charAt(row*6+col)=='1'?Color.WHITE:Color.BLACK);
        canvas.drawRect(x+(col+1)*cell,y+(row+1)*cell,x+(col+2)*cell,y+(row+2)*cell,p);
      }
    }
  }
}
