from .base import ISensor
import random

class VoltageSensor(ISensor):
    def __init__(self, name='voltage_sim', min_v=11.5, max_v=13.0):
        self.name = name
        self.min_v = min_v
        self.max_v = max_v

    def read(self):
        return {
            'sensor': self.name,
            'type': 'voltage',
            'value': round(random.uniform(self.min_v, self.max_v), 3)
        }
