from abc import ABC, abstractmethod


class OCRBackend(ABC):
    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """Extract raw text from a pre-processed image file path."""
        ...
