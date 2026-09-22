package dev.atul.capsulemap;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Bounded, byte-counted HTTP transport for the local controller. */
final class LocalHttp implements AutoCloseable {
    interface Router { String route(String method, String path, String body) throws Exception; }
    static final class Failure extends Exception {
        private static final long serialVersionUID=1L;
        final int status;
        Failure(int status, String message) { super(message); this.status=status; }
    }
    private final ServerSocket server;
    private final Set<Socket> clients=Collections.synchronizedSet(new HashSet<Socket>());
    private final ThreadPoolExecutor pool=new ThreadPoolExecutor(4,4,0,TimeUnit.SECONDS,new ArrayBlockingQueue<Runnable>(12));
    LocalHttp(int port, final Router router) throws IOException {
        server=new ServerSocket(); server.setReuseAddress(true); server.bind(new InetSocketAddress(port));
        new Thread(new Runnable(){public void run(){
            while(!server.isClosed()) try {
                final Socket socket=server.accept(); socket.setSoTimeout(4000); clients.add(socket);
                try {pool.execute(new Runnable(){public void run(){handle(socket,router);}});}
                catch(RejectedExecutionException e){clients.remove(socket);socket.close();}
            } catch(IOException e){if(!server.isClosed())android.util.Log.w("CapsuleHttp","Accept failed",e);}
        }},"CapsuleHttp").start();
    }
    static String line(InputStream in) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        for(int c;(c=in.read())!=-1;){
            if(c==10){byte[] b=out.toByteArray();if(b.length==0||b[b.length-1]!=13)throw new Failure(400,"Invalid HTTP line");return new String(b,0,b.length-1,StandardCharsets.US_ASCII);}
            if(out.size()>=4096)throw new Failure(431,"Header line too long");out.write(c);
        }
        throw new Failure(400,"Incomplete request");
    }
    private void handle(Socket s, Router router) {
        try {
            int status=200;String result;String mime="application/json; charset=utf-8";
            try {
                final long deadline=android.os.SystemClock.elapsedRealtime()+8000;
                InputStream in=new BufferedInputStream(s.getInputStream()){
                    void check() throws SocketTimeoutException {if(android.os.SystemClock.elapsedRealtime()>deadline)throw new SocketTimeoutException();}
                    public synchronized int read() throws IOException {check();return super.read();}
                    public synchronized int read(byte[] b,int off,int len) throws IOException {check();return super.read(b,off,len);}
                };
                String[] first=line(in).split(" ");
                if(first.length!=3||!first[2].startsWith("HTTP/1."))throw new Failure(400,"Invalid request line");
                int size=0;Map<String,String> headers=new HashMap<String,String>();
                for(String h;!(h=line(in)).isEmpty();){
                    size+=h.length()+2;if(size>16384)throw new Failure(431,"Headers too large");
                    int at=h.indexOf(':');if(at<=0)throw new Failure(400,"Invalid header");
                    String key=h.substring(0,at).toLowerCase(Locale.US);
                    if(headers.containsKey(key))throw new Failure(400,"Duplicate header");
                    headers.put(key,h.substring(at+1).trim());
                }
                if(headers.containsKey("transfer-encoding"))throw new Failure(400,"Chunked requests unsupported");
                int length=0;
                if(headers.containsKey("content-length"))try{length=Integer.parseInt(headers.get("content-length"));}catch(NumberFormatException e){throw new Failure(400,"Invalid content length");}
                if(length<0)throw new Failure(400,"Invalid content length");
                if(length>262144)throw new Failure(413,"Request exceeds 256 KiB");
                if(first[0].equals("POST")&&!headers.containsKey("content-length"))throw new Failure(411,"Content length required");
                byte[] data=new byte[length];int n=0;
                while(n<length){int k=in.read(data,n,length-n);if(k<0)throw new Failure(400,"Incomplete request body");n+=k;}
                result=router.route(first[0],first[1],new String(data,StandardCharsets.UTF_8));
                if(first[1].equals("/"))mime="text/html; charset=utf-8";
            }catch(SocketTimeoutException e){status=408;result=error("Request timed out");}
             catch(Failure e){status=e.status;result=error(e.getMessage());}
             catch(org.json.JSONException e){status=400;result=error(e.getMessage());}
             catch(Exception e){status=500;result=error("Request failed");android.util.Log.e("CapsuleHttp","Request failed",e);}
            byte[] out=result.getBytes(StandardCharsets.UTF_8);
            OutputStream stream=s.getOutputStream();
            stream.write(("HTTP/1.1 "+status+" Result\r\nContent-Type: "+mime+"\r\nContent-Length: "+out.length+"\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));stream.write(out);stream.flush();
        }catch(IOException ignored){}finally{clients.remove(s);try{s.close();}catch(IOException ignored){}}
    }
    static String error(String message){return "{\"error\":"+org.json.JSONObject.quote(message)+"}";}
    public void close(){try{server.close();}catch(IOException ignored){} synchronized(clients){for(Socket s:clients)try{s.close();}catch(IOException ignored){}clients.clear();}pool.shutdownNow();}
}
