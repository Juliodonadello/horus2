"""Node simulator: spawn multiple simulated nodes that post readings to backend.

Usage:
  python node_simulator.py --nodes 3 --interval 5 --backend http://localhost:8000/ingest

The script imports the sensors package from the repo and sends JSON payloads similar to `edge/collector.py`.
"""
import argparse
import time
import random
import requests
import threading
from sensors.voltage_sensor import VoltageSensor
from sensors.current_sensor import CurrentSensor


def node_loop(site_id, backend_url, interval):
    v = VoltageSensor(name=f"voltage_{site_id}")
    c = CurrentSensor(name=f"current_{site_id}")
    while True:
        payload = {
            'site_id': site_id,
            'timestamp': int(time.time()),
            'readings': [v.read(), c.read()]
        }
        try:
            resp = requests.post(backend_url, json=payload, timeout=5)
            print(f"[{site_id}] sent -> {resp.status_code}")
        except Exception as e:
            print(f"[{site_id}] error sending: {e}")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', type=int, default=2)
    parser.add_argument('--interval', type=int, default=5)
    parser.add_argument('--backend', type=str, default='http://localhost:8000/ingest')
    args = parser.parse_args()

    threads = []
    for i in range(args.nodes):
        site_id = f"site_{i+1:03d}"
        t = threading.Thread(target=node_loop, args=(site_id, args.backend, args.interval), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.2)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping simulators')


if __name__ == '__main__':
    main()
