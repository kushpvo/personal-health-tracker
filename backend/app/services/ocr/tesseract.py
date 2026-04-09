import pytesseract
from PIL import Image
from app.services.ocr.base import OCRBackend


class TesseractBackend(OCRBackend):
    def __init__(self, lang: str = "eng", config: str = "--psm 6"):
        self.lang = lang
        self.config = config

    def extract_text(self, image_path: str) -> str:
        image = Image.open(image_path)
        return pytesseract.image_to_string(image, lang=self.lang, config=self.config)
