# Edge collector (HTTP) - simula sensores y envía lecturas vía HTTP al backend
import time, os, requests, json
from sensors.voltage_sensor import VoltageSensor
from sensors.current_sensor import CurrentSensor

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000/ingest')
INTERVAL = int(os.environ.get('INTERVAL', '5'))

def main():
    v = VoltageSensor()
    c = CurrentSensor()
    print('Edge collector started. Sending to', BACKEND_URL)
    while True:
        data = {
            'site_id': 'site_001',
            'timestamp': int(time.time()),
            'readings': [v.read(), c.read()]
        }
        try:
            resp = requests.post(BACKEND_URL, json=data, timeout=5)
            print('Sent:', data, '->', resp.status_code)
        except Exception as e:
            print('Error sending data:', e)
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
