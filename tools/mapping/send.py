#!/usr/bin/env python3
"""Send a saved scene/mapping payload to Capsule Map over the local network."""
import argparse,json,pathlib,urllib.request
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--host',required=True,help='http://PROJECTOR_IP:8765')
p.add_argument('--pin',required=True)
p.add_argument('scene',type=pathlib.Path)
a=p.parse_args();data=json.loads(a.scene.read_text());data['pin']=a.pin
req=urllib.request.Request(a.host.rstrip('/')+'/scene',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=10) as r:print(r.read().decode())
