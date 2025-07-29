import os
import base64
import json
import csv
import pytesseract
from io import StringIO
from PIL import Image
import PyPDF2
import requests


def file_to_text(file_path: str) -> str:
    """
    Extract text from various file types (CSV, PDF, PNG, JPG, JSON)
    with appropriate processing for each format.
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in [".png", ".jpg", ".jpeg"]:
            # OCR processing for images
            img = Image.open(file_path)
            return pytesseract.image_to_string(img)

        elif ext == ".pdf":
            # PDF text extraction
            text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text

        elif ext == ".csv":
            # Convert CSV to readable text
            with open(file_path, "r") as f:
                reader = csv.reader(f)
                output = StringIO()
                writer = csv.writer(output)
                writer.writerows(reader)
                return output.getvalue()

        elif ext == ".json":
            # Convert JSON to formatted string
            with open(file_path, "r") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)

        else:
            # Fallback for other file types
            with open(file_path, "r", errors="ignore") as f:
                return f.read(5000)  # Read first 5000 characters

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return "File content could not be extracted"
