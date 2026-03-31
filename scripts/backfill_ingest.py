#!/usr/bin/env python3
"""Backfill historical voltage/current readings by posting to backend /ingest.

Usage: python scripts/backfill_ingest.py --hours 24 --step 60 --sites cordoba_capital rio_cuarto

This posts one event per site per timestamp containing voltage and current readings.
"""
import argparse
import time
import math
import random
import requests
from datetime import datetime, timedelta


def make_readings(site_id, ts, voltage_v=48.0, current_max=10.0, irr_factor=1.0):
    # add a small diurnal variation using timestamp hour
    hour = datetime.utcfromtimestamp(ts).hour
    # simple solar curve: 0 at night, peak at noon
    day_frac = max(0.0, math.sin(math.pi * (hour - 6) / 12.0))
    irr = day_frac * irr_factor

    # voltage around nominal with slight variance
    v = voltage_v + (irr * random.uniform(-1.5, 2.5)) + random.uniform(-0.2, 0.2)
    # current proportional to irradiance
    c = max(0.0, irr * current_max * (0.6 + random.random() * 0.8))

    return [
        {'sensor': f'voltage_{site_id}', 'type': 'voltage', 'value': round(v, 3)},
        {'sensor': f'current_{site_id}', 'type': 'current', 'value': round(c, 3)}
    ]


def run_backfill(backend_url, sites, start_ts, end_ts, step, sleep_per=0.0):
    ts = start_ts
    total = 0
    session = requests.Session()
    while ts <= end_ts:
        for site in sites:
            readings = make_readings(site, ts)
            payload = {
                'site_id': site,
                'timestamp': int(ts),
                'readings': readings
            }
            try:
                resp = session.post(backend_url, json=payload, timeout=5)
                if resp.status_code != 200:
                    print(f'WARN: backend returned {resp.status_code} for {site} @{ts}: {resp.text}')
                else:
                    total += 1
            except Exception as e:
                print('ERROR posting', e)

        if sleep_per:
            time.sleep(sleep_per)
        ts += step

    print(f'Backfill complete, events posted: {total}')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', default='http://localhost:8000/ingest', help='Backend ingest URL')
    p.add_argument('--hours', type=int, default=24, help='How many hours to backfill')
    p.add_argument('--step', type=int, default=60, help='Time step in seconds between samples')
    p.add_argument('--sites', nargs='+', default=['cordoba_capital', 'rio_cuarto', 'villa_maria', 'san_francisco'])
    p.add_argument('--sleep', type=float, default=0.0, help='Sleep seconds between timestamp batches')
    return p.parse_args()


def main():
    args = parse_args()
    now = int(time.time())
    start = now - args.hours * 3600
    end = now
    print(f'Backfilling {args.hours} hours from {datetime.utcfromtimestamp(start)} to {datetime.utcfromtimestamp(end)}')
    run_backfill(args.backend, args.sites, start, end, args.step, sleep_per=args.sleep)


if __name__ == '__main__':
    main()
