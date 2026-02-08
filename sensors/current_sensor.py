from .base import ISensor
import random

class CurrentSensor(ISensor):
    """Simulated current sensor with realistic battery current range."""
    
    def __init__(self, name='current_sim', min_a=0.0, max_a=5.0, noise=0.1):
        """
        Args:
            name: Sensor identifier
            min_a: Minimum current (default 0A for idle)
            max_a: Maximum current (default 5A for typical battery draw)
            noise: Random noise amplitude (±A) for realistic readings
        """
        self.name = name
        self.min_a = min_a
        self.max_a = max_a
        self.noise = noise
        self.last_value = min_a  # Start at minimum (idle)

    def read(self):
        """Return current reading with variation for realism."""
        # Add random walk for more realistic behavior (consumption/charging patterns)
        delta = random.uniform(-self.noise, self.noise)
        self.last_value = max(self.min_a, min(self.max_a, self.last_value + delta))
        
        return {
            'sensor': self.name,
            'type': 'current',
            'value': round(self.last_value, 3)
        }
