from .base_sensor import BaseSensor
import random

class ACVoltageSensor(BaseSensor):
    def __init__(self, name, min_value=210, max_value=230):
        super().__init__(name, "AC Voltage", min_value, max_value)

    def read_value(self):
        return random.uniform(self.min_value, self.max_value)

class DCVoltageSensor(BaseSensor):
    def __init__(self, name, min_value=11.5, max_value=12.5):
        super().__init__(name, "DC Voltage", min_value, max_value)

    def read_value(self):
        return random.uniform(self.min_value, self.max_value)
