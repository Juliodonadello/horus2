from .base import ISensor
import random

class VoltageSensor(ISensor):
    """Simulated voltage sensor tuned for ~48V solar panels.

    Defaults produce values around 48V (typical PV array nominal),
    with a small random walk to keep readings coherent.
    """

    def __init__(self, name='voltage_sim', min_v=44.0, max_v=52.0, noise=0.2):
        self.name = name
        self.min_v = min_v
        self.max_v = max_v
        self.noise = noise
        self.last_value = (min_v + max_v) / 2

    def read(self):
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_v, min(self.max_v, self.last_value + delta))
        return {
            'sensor': self.name,
            'type': 'voltage',
            'value': round(self.last_value, 3)
        }
