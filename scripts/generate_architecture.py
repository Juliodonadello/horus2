#!/usr/bin/env python3
"""Generate a simple architecture JPG for Horus2 using Pillow.

Creates `docs/architecture.jpg` with labeled boxes and arrows.
If Pillow is not installed, prints instructions to install it.
"""
from pathlib import Path
import sys

OUT = Path('docs') / 'architecture.jpg'

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print('Pillow is required. Install with: pip install pillow')
    sys.exit(2)

# Canvas
W, H = 1200, 800
img = Image.new('RGB', (W, H), 'white')
draw = ImageDraw.Draw(img)

def box(x, y, w, h, text):
    draw.rectangle([x, y, x+w, y+h], outline='black', width=2, fill='#f0f4f8')
    # simple text wrap
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x+8, y+8), text, fill='black', font=font)

def arrow(x1, y1, x2, y2):
    draw.line([x1, y1, x2, y2], fill='black', width=2)
    # arrowhead
    import math
    angle = math.atan2(y2-y1, x2-x1)
    l = 10
    a1 = angle + math.radians(150)
    a2 = angle - math.radians(150)
    draw.line([x2, y2, x2 + l*math.cos(a1), y2 + l*math.sin(a1)], fill='black', width=2)
    draw.line([x2, y2, x2 + l*math.cos(a2), y2 + l*math.sin(a2)], fill='black', width=2)

# Draw components
box(50, 50, 220, 80, 'Docker Compose\n(orchestration)')
box(50, 170, 300, 100, 'edge/\nedge collector\n(sensors package)')
box(420, 120, 320, 140, 'backend/\nFastAPI /ingest\nWrites to InfluxDB + Postgres')
box(780, 60, 320, 140, 'InfluxDB\nhorus-bucket\n(timeseries)')
box(780, 220, 320, 120, 'Postgres\nevents table')
box(420, 320, 300, 120, 'Grafana\nprovisioning: datasources & dashboards')
box(50, 320, 300, 120, 'tests/\nnode_simulator.py\n(simulated nodes)')

# Arrows
arrow(170, 130, 420, 170)   # edge -> backend
arrow(600, 200, 780, 120)   # backend -> influx
arrow(600, 200, 880, 260)   # backend -> postgres
arrow(880, 180, 600, 320)   # influx -> grafana
arrow(200, 380, 420, 380)   # nodes -> backend

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, quality=90)
print(f'Wrote {OUT}')
