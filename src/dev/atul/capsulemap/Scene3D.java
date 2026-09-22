package dev.atul.capsulemap;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import org.json.*;
import java.util.*;

/** Small CPU mesh renderer: rotation, perspective projection, depth-sorted shaded faces. */
final class Scene3D {
    final float[][] vertices;
    final int[][] faces;
    final int color;
    final float speed;
    final String name;
    final JSONObject json;

    Scene3D(JSONObject input) throws JSONException {
        json = new JSONObject(input.toString());
        name = json.optString("name", "3D mesh");
        if (name.length() > 80) throw new JSONException("Scene name too long");
        JSONArray vv=json.getJSONArray("vertices"), ff=json.getJSONArray("faces");
        if(vv.length()<4 || vv.length()>128 || ff.length()<1 || ff.length()>256) throw new JSONException("Mesh size out of bounds");
        vertices=new float[vv.length()][3]; faces=new int[ff.length()][];
        for(int i=0;i<vertices.length;i++) {
            JSONArray v=vv.getJSONArray(i);
            if(v.length()!=3) throw new JSONException("Each vertex needs xyz");
            for(int j=0;j<3;j++) {
                double n=v.getDouble(j);
                if(Double.isNaN(n)||Double.isInfinite(n)||Math.abs(n)>1.5) throw new JSONException("Vertex coordinates must be finite and within +/-1.5");
                vertices[i][j]=(float)n;
            }
        }
        for(int i=0;i<faces.length;i++) {
            JSONArray f=ff.getJSONArray(i);
            if(f.length()<3||f.length()>8) throw new JSONException("Faces need 3-8 vertices");
            faces[i]=new int[f.length()];
            for(int j=0;j<f.length();j++) {
                double raw=f.getDouble(j); int index=(int)raw;
                if(raw!=index||index<0||index>=vertices.length) throw new JSONException("Invalid face index");
                faces[i][j]=index;
            }
        }
        double rate=json.optDouble("speed",0.45);
        if(Double.isNaN(rate)||Double.isInfinite(rate)||Math.abs(rate)>2) throw new JSONException("Invalid speed");
        speed=(float)rate;
        try {color=Color.parseColor(json.optString("color","#42ddff"));}
        catch(IllegalArgumentException e){throw new JSONException("Invalid color");}
    }

    void draw(Canvas c, Paint paint, float time) {
        paint.setStyle(Paint.Style.FILL); paint.setColor(Color.rgb(2,5,14)); c.drawRect(0,0,1000,600,paint);
        // Receding lines establish depth around the rotating geometry.
        paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(1.5f); paint.setColor(Color.rgb(18,55,78));
        for(int i=-8;i<=8;i++) c.drawLine(500+i*24,300,500+i*110,600,paint);
        for(int i=0;i<9;i++){float y=310+(float)Math.pow(i/8f,2)*290; c.drawLine(0,y,1000,y,paint);}
        final float[][] transformed=new float[vertices.length][3];
        float[][] screen=new float[vertices.length][2];
        double a=time*speed, b=.32+Math.sin(time*.27)*.16;
        for(int i=0;i<vertices.length;i++) {
            float[] v=vertices[i];
            float x=(float)(v[0]*Math.cos(a)+v[2]*Math.sin(a));
            float z=(float)(-v[0]*Math.sin(a)+v[2]*Math.cos(a));
            float y=(float)(v[1]*Math.cos(b)-z*Math.sin(b));
            z=(float)(v[1]*Math.sin(b)+z*Math.cos(b));
            transformed[i]=new float[]{x,y,z};
            float scale=780/(6-z);
            screen[i][0]=500+x*scale; screen[i][1]=285-y*scale;
        }
        Integer[] order=new Integer[faces.length]; final float[] depth=new float[faces.length];
        for(int i=0;i<faces.length;i++){order[i]=i;for(int index:faces[i])depth[i]+=transformed[index][2]/faces[i].length;}
        Arrays.sort(order,new Comparator<Integer>(){public int compare(Integer a,Integer b){return Float.compare(depth[a],depth[b]);}});
        for(int index:order) {
            int[] f=faces[index];float[] v0=transformed[f[0]],v1=transformed[f[1]],v2=transformed[f[2]];
            float ux=v1[0]-v0[0],uy=v1[1]-v0[1],uz=v1[2]-v0[2];
            float vx=v2[0]-v0[0],vy=v2[1]-v0[1],vz=v2[2]-v0[2];
            float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
            float length=(float)Math.sqrt(nx*nx+ny*ny+nz*nz);
            float light=.25f+.75f*Math.abs((nx*.3f+ny*.5f+nz*.8f)/Math.max(.001f,length));
            light=Math.min(1,light);
            Path path=new Path();path.moveTo(screen[f[0]][0],screen[f[0]][1]);
            for(int j=1;j<f.length;j++)path.lineTo(screen[f[j]][0],screen[f[j]][1]);path.close();
            paint.setStyle(Paint.Style.FILL);paint.setColor(Color.rgb((int)(Color.red(color)*light),(int)(Color.green(color)*light),(int)(Color.blue(color)*light)));c.drawPath(path,paint);
            paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(2.5f);paint.setColor(Color.rgb(190,240,255));c.drawPath(path,paint);
        }
        paint.setStyle(Paint.Style.FILL);
    }
}
