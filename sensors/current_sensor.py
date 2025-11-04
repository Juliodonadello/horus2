from .base import ISensor
import random

class CurrentSensor(ISensor):
    def __init__(self, name='current_sim', min_a=0.0, max_a=5.0):
        self.name = name
        self.min_a = min_a
        self.max_a = max_a

    def read(self):
        return {
            'sensor': self.name,
            'type': 'current',
            'value': round(random.uniform(self.min_a, self.max_a), 3)
        }
