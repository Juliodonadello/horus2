from .base_sensor import BaseSensor
import random

class ACCurrentSensor(BaseSensor):
    def __init__(self, name, min_value=0.5, max_value=2.0):
        super().__init__(name, "AC Current", min_value, max_value)

    def read_value(self):
        return random.uniform(self.min_value, self.max_value)

class DCCurrentSensor(BaseSensor):
    def __init__(self, name, min_value=0.1, max_value=0.5):
        super().__init__(name, "DC Current", min_value, max_value)

    def read_value(self):
        return random.uniform(self.min_value, self.max_value)
