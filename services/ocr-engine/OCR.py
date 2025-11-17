# OCR.py
import os
from io import BytesIO
from typing import Union

import fitz  # PyMuPDF
from PIL import Image
from google.cloud import vision
from google.oauth2 import service_account

class OCR:
    def __init__(self):
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not key_path or not os.path.exists(key_path):
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS is not set or file not found"
            )
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self.client = vision.ImageAnnotatorClient(credentials=credentials)

    def _pdf_pages_to_png_bytes_from_path(self, pdf_path: str, dpi: int = 200):
        png_bytes_list = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                mode = "RGBA" if pix.alpha else "RGB"
                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if mode == "RGBA":
                    img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="PNG")
                png_bytes_list.append(buf.getvalue())
        return png_bytes_list

    def _pdf_pages_to_png_bytes_from_bytes(self, pdf_bytes: bytes, dpi: int = 200):
        png_bytes_list = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=dpi)
                mode = "RGBA" if pix.alpha else "RGB"
                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if mode == "RGBA":
                    img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="PNG")
                png_bytes_list.append(buf.getvalue())
        return png_bytes_list

    def perform_ocr(self, input_data: Union[str, bytes]) -> str:
        """
        Run OCR on a PDF provided either as a filesystem path (str) or raw bytes.
        Returns concatenated text.
        """
        if isinstance(input_data, str):
            page_pngs = self._pdf_pages_to_png_bytes_from_path(input_data)
        elif isinstance(input_data, (bytes, bytearray, memoryview)):
            page_pngs = self._pdf_pages_to_png_bytes_from_bytes(bytes(input_data))
        else:
            raise TypeError("perform_ocr expects a file path (str) or PDF bytes.")

        extracted_text = []
        for content in page_pngs:
            image = vision.Image(content=content)
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                raise RuntimeError(f"Vision API error: {response.error.message}")

            if response.full_text_annotation and response.full_text_annotation.text:
                extracted_text.append(response.full_text_annotation.text)
            elif response.text_annotations:
                extracted_text.append(response.text_annotations[0].description)
            else:
                extracted_text.append("")

        return "\n\n".join(extracted_text)