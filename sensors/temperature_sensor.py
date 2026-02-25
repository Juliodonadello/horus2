from .base import ISensor
import random

class TemperatureSensor(ISensor):
    """Simulated panel temperature sensor (°C)."""

    def __init__(self, name='temp_sim', min_c=10.0, max_c=70.0, noise=0.5):
        self.name = name
        self.min_c = min_c
        self.max_c = max_c
        self.noise = noise
        self.last_value = (min_c + max_c) / 2

    def read(self):
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_c, min(self.max_c, self.last_value + delta))
        return {
            'sensor': self.name,
            'type': 'temperature',
            'value': round(self.last_value, 2)
        }
