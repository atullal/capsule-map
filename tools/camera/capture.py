#!/usr/bin/env python3
"""Save an internal-camera JPEG without projecting the factory photo preview."""
import argparse,json
from sensor import Sensor
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--serial',required=True);p.add_argument('--output',required=True);a=p.parse_args()
print(json.dumps(Sensor(a.serial).capture(a.output),indent=2))
