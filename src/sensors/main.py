import threading
import requests
import datetime
import time
import random
from voltage_sensor import ACVoltageSensor, DCVoltageSensor
from current_sensor import ACCurrentSensor, DCCurrentSensor

API_URL = "http://127.0.0.1:8000/sensors/"

def run_sensor(sensor):
    while True:
        value = sensor.read_value()
        timestamp = datetime.datetime.now().isoformat()
        payload = {
            "sensor_name": sensor.name,
            "sensor_type": sensor.sensor_type,
            "value": value,
            "timestamp": timestamp
        }
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"[{sensor.name}] Stored {sensor.sensor_type}: {value}")
            else:
                print(f"[{sensor.name}] Error storing data: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"[{sensor.name}] Error connecting to API: {e}")

        time.sleep(random.uniform(1, 5))

if __name__ == "__main__":
    sensors = [
        ACVoltageSensor("AC Voltage Sensor 1"),
        DCVoltageSensor("DC Voltage Sensor 1"),
        ACCurrentSensor("AC Current Sensor 1"),
        DCCurrentSensor("DC Current Sensor 1"),
    ]

    threads = []
    for sensor in sensors:
        thread = threading.Thread(target=run_sensor, args=(sensor,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
