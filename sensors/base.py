from abc import ABC, abstractmethod

class ISensor(ABC):
    @abstractmethod
    def read(self) -> dict:
        """Return a dict with sensor readings."""
        raise NotImplementedError
