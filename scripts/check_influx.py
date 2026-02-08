#!/usr/bin/env python3
import json
import urllib.request

INFLUX_URL = 'http://localhost:8086/api/v2/query?org=horus-org'
TOKEN = 'my-influx-token'

query = '''from(bucket: "horus-bucket")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "sensor_readings")
  |> limit(n: 20)
'''

req = urllib.request.Request(INFLUX_URL, data=json.dumps({'query': query}).encode('utf-8'),
                             headers={
                                 'Content-Type': 'application/json',
                                 'Authorization': f'Token {TOKEN}',
                                 'Accept': 'application/json'
                             })
with urllib.request.urlopen(req, timeout=10) as resp:
    body = resp.read().decode('utf-8')
    try:
        j = json.loads(body)
        print(json.dumps(j, indent=2)[:10000])
    except Exception:
        print(body[:10000])
