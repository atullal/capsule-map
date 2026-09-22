#!/usr/bin/env python3
"""Exercise mesh validation on a running projector without changing its scene."""
import argparse,copy,json,urllib.request,urllib.error
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True);p.add_argument('--pin',required=True);a=p.parse_args()
base=a.host.rstrip('/')
def state():return json.load(urllib.request.urlopen(base+'/state',timeout=10))
def send(v):
 try:
  with urllib.request.urlopen(urllib.request.Request(base+'/scene',data=json.dumps(v).encode(),headers={'Content-Type':'application/json'}),timeout=10) as r:return r.status
 except urllib.error.HTTPError as e:return e.code
old=state();assert old['mode']=='mesh3d'
payload={'pin':a.pin,'scene':old['scene'],'corners':old['corners'],'guides':old['guides']}
wrong=copy.deepcopy(payload);wrong['pin']='wrong';assert send(wrong)==403
bad=copy.deepcopy(payload);bad['scene']['faces'][0][0]=999;assert send(bad)==400
bad=copy.deepcopy(payload);bad['corners']=[.1,.1,.9,.9,.9,.1,.1,.9];assert send(bad)==400
assert state()==old
print('PASS: invalid PIN, face index and crossed corners rejected without state mutation.')
