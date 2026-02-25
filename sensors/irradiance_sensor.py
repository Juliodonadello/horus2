from .base import ISensor
import random

class IrradianceSensor(ISensor):
    """Simulated irradiance sensor (W/m^2)."""

    def __init__(self, name='irradiance_sim', min_w=0.0, max_w=1000.0, noise=20.0):
        self.name = name
        self.min_w = min_w
        self.max_w = max_w
        self.noise = noise
        self.last_value = (min_w + max_w) / 2

    def read(self):
        # larger swings for irradiance to simulate sun/cloud
        delta = random.uniform(-self.noise*2, self.noise*2)
        self.last_value = max(self.min_w, min(self.max_w, self.last_value + delta))
        return {
            'sensor': self.name,
            'type': 'irradiance',
            'value': round(self.last_value, 1)
        }
