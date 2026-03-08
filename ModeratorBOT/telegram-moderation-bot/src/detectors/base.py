from abc import ABC, abstractmethod
from typing import Any

class BaseDetector(ABC):
    """
    Abstract base class for all content and user activity detectors.
    """
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def detect(self, *args, **kwargs) -> Any:
        """
        Main logic for detection. Must be implemented by subclasses.
        Returns a specific Result dataclass.
        """
        pass
