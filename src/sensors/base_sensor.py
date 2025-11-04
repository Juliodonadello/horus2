import random
import time

class BaseSensor:
    def __init__(self, name, sensor_type, min_value, max_value):
        self.name = name
        self.sensor_type = sensor_type
        self.min_value = min_value
        self.max_value = max_value

    def read_value(self):
        raise NotImplementedError("This method should be implemented by subclasses")

    def simulate(self, interval=1):
        while True:
            value = self.read_value()
            print(f"[{self.name}] {self.sensor_type}: {value}")
            time.sleep(interval)
