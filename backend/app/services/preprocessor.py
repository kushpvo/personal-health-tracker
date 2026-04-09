import os
import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale, denoise, and threshold for better OCR accuracy."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def prepare_images(file_path: str) -> List[str]:
    """
    Convert file (PDF or image) to pre-processed PNG images.
    Returns list of temporary file paths. Caller is responsible for cleanup.
    """
    suffix = Path(file_path).suffix.lower()
    tmp_dir = tempfile.mkdtemp()
    output_paths: List[str] = []

    if suffix == ".pdf":
        from pdf2image import convert_from_path
        pages = convert_from_path(file_path, dpi=300)
        pil_images = pages
    else:
        pil_images = [Image.open(file_path).convert("RGB")]

    for i, pil_img in enumerate(pil_images):
        arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        processed = _preprocess_image(arr)
        out_path = os.path.join(tmp_dir, f"page_{i:03d}.png")
        cv2.imwrite(out_path, processed)
        output_paths.append(out_path)

    return output_paths
