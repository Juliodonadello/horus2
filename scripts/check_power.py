#!/usr/bin/env python3
import json
import urllib.request

INFLUX_URL = 'http://localhost:8086/api/v2/query?org=horus-org'
TOKEN = 'my-influx-token'

query = '''v = from(bucket: 'horus-bucket') |> range(start: -15m) |> filter(fn: (r) => r._measurement == 'sensor_readings' and r._field == 'value' and r.type == 'voltage') |> aggregateWindow(every: 10s, fn: mean, createEmpty: false) |> rename(columns: {_value: 'voltage'})

c = from(bucket: 'horus-bucket') |> range(start: -15m) |> filter(fn: (r) => r._measurement == 'sensor_readings' and r._field == 'value' and r.type == 'current') |> aggregateWindow(every: 10s, fn: mean, createEmpty: false) |> rename(columns: {_value: 'current'})

join(tables: {v:v, c:c}, on: ['_time', 'sensor']) |> map(fn: (r) => ({_value: r.voltage * r.current}))'''

req = urllib.request.Request(INFLUX_URL, data=json.dumps({'query': query}).encode('utf-8'),
                             headers={'Content-Type': 'application/json', 'Authorization': f'Token {TOKEN}'})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(resp.read().decode('utf-8')[:10000])
