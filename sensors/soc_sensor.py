from .base import ISensor
import random

class SOCSensor(ISensor):
    """Simulated state-of-charge (%) sensor with slow random walk."""

    def __init__(self, name='soc_sim', min_pct=20.0, max_pct=100.0, noise=0.2):
        self.name = name
        self.min_pct = min_pct
        self.max_pct = max_pct
        self.noise = noise
        self.last_value = (min_pct + max_pct) / 2

    def read(self):
        # slow drift
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_pct, min(self.max_pct, self.last_value + delta))
        return {
            'sensor': self.name,
            'type': 'soc',
            'value': round(self.last_value, 2)
        }
