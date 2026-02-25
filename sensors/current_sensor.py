from .base import ISensor
import random

class CurrentSensor(ISensor):
    """Simulated current sensor for PV systems (higher range than small battery).

    Defaults target a more realistic PV current range for 48V systems.
    """

    def __init__(self, name='current_sim', min_a=0.0, max_a=20.0, noise=0.5):
        self.name = name
        self.min_a = min_a
        self.max_a = max_a
        self.noise = noise
        self.last_value = (min_a + max_a) / 10.0

    def read(self):
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_a, min(self.max_a, self.last_value + delta))
        return {
            'sensor': self.name,
            'type': 'current',
            'value': round(self.last_value, 3)
        }
