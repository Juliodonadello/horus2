from .base import ISensor
import random

class VoltageSensor(ISensor):
    """Simulated voltage sensor with realistic battery voltage range."""
    
    def __init__(self, name='voltage_sim', min_v=11.5, max_v=13.5, noise=0.05):
        """
        Args:
            name: Sensor identifier
            min_v: Minimum voltage (default 11.5V for discharged 12V battery)
            max_v: Maximum voltage (default 13.5V for charged 12V battery)
            noise: Random noise amplitude (±V) for realistic readings
        """
        self.name = name
        self.min_v = min_v
        self.max_v = max_v
        self.noise = noise
        self.last_value = (min_v + max_v) / 2  # Start at middle value

    def read(self):
        """Return voltage reading with slight variation for realism."""
        # Add small random walk for more realistic behavior
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_v, min(self.max_v, self.last_value + delta))
        
        return {
            'sensor': self.name,
            'type': 'voltage',
            'value': round(self.last_value, 3)
        }
