import os
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

class OCR:
    def __init__(self):
        key_path = os.getenv("VISION_CREDENTIALS")
        if not key_path or not os.path.exists(key_path):
            raise RuntimeError(
                "VISION_CREDENTIALS is not set or file not found"
            )
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self.client = vision.ImageAnnotatorClient(credentials=credentials)

    def _pdf_pages_to_png_bytes(self, pdf_path: str, dpi: int = 200):
        """Render each PDF page to PNG bytes suitable for Vision API."""
        png_bytes_list = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                mode = "RGBA" if pix.alpha else "RGB"
                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if mode == "RGBA":
                    img = img.convert("RGB")  # Vision prefers RGB
                buf = BytesIO()
                img.save(buf, format="PNG")
                png_bytes_list.append(buf.getvalue())
        return png_bytes_list

    def perform_ocr(self, input_path: str) -> str:
        """Run OCR on a PDF and return concatenated text."""
        extracted_text = []
        for content in self._pdf_pages_to_png_bytes(input_path):
            image = vision.Image(content=content)
            # DOCUMENT_TEXT_DETECTION is better for dense text (PDFs)
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                # surface API errors clearly
                raise RuntimeError(f"Vision API error: {response.error.message}")

            # Prefer full_text_annotation when available
            if response.full_text_annotation and response.full_text_annotation.text:
                extracted_text.append(response.full_text_annotation.text)
            elif response.text_annotations:
                extracted_text.append(response.text_annotations[0].description)
            else:
                extracted_text.append("")

        return "\n\n".join(extracted_text)
