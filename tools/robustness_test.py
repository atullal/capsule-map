"""Device integration checks: invalid requests must not mutate mapping; valid Unicode survives."""
import argparse,json,socket,urllib.request,urllib.error,concurrent.futures
p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--pin',required=True);a=p.parse_args()
base='http://'+a.host+':8765'
def get(path):return json.load(urllib.request.urlopen(base+path,timeout=12))
def post(path,payload):
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'}),timeout=12) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
def mapping(v):return {k:v[k] for k in ('prompt','corners','guides','mappingMode')}
def raw(data):
 with socket.create_connection((a.host,8765),timeout=8) as s:
  s.sendall(data);s.shutdown(socket.SHUT_WR);buf=b''
  while True:
   part=s.recv(65536)
   if not part:break
   buf+=part
  return int(buf.split(b' ')[1])
old=get('/state');before=mapping(old)
assert post('/update',{'pin':'wrong','prompt':'changed'})[0]==403
for fields in [{'prompt':'changed','corners':[.1,.1,.9,.9,.9,.1,.1,.9]},{'corners':[0,0]},{'guides':'false'},{'prompt':'x'*181}]:
 assert post('/update',dict(pin=a.pin,**fields))[0]==400
 assert mapping(get('/state'))==before
assert raw(b'POST /update HTTP/1.1\r\nContent-Length: -1\r\n\r\n')==400
assert raw(b'POST /update HTTP/1.1\r\nContent-Length: 262145\r\n\r\n')==413
assert raw(b'POST /update HTTP/1.1\r\nContent-Length: 10\r\n\r\n{}')==400
assert raw(b'POST /update HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n{}')==400
assert raw(b'POST /update HTTP/1.1\r\nContent-Length: 1\r\n\r\n{')==400
assert raw(b'GET /update HTTP/1.1\r\n\r\n')==405
for file in ['../life-and-love.mp4','missing.mp4']:
 assert post('/media',{'pin':a.pin,'action':'play','file':file})[0]==400
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 assert all(v['server']=='Listening' for v in pool.map(lambda _:get('/state'),range(24)))
try:
 text='ocean 🌊 — रात'
 assert post('/update',{'pin':a.pin,'prompt':text})[0]==200
 assert get('/state')['prompt']==text
finally:
 assert post('/update',dict(pin=a.pin,**{k:old[k] for k in ('prompt','corners','guides')}))[0]==200
 if old['mappingMode']=='mesh3d':payload={'pin':a.pin,'scene':old['scene'],'corners':old['corners'],'guides':old['guides']};assert post('/scene',payload)[0]==200
 assert mapping(get('/state'))==before
print('PASS: authentication, atomic validation, malformed HTTP, Unicode, concurrency, media path validation and mapping restoration')
