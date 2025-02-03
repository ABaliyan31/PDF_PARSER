import io
import boto3
from botocore.exceptions import NoCredentialsError
from sanic import json
from pdf2image import convert_from_bytes
import pytesseract
import aiohttp
import datetime
import fitz  # PyMuPDF
import asyncio
from botocore.client import Config
from config import config

minio_config = config["MINIO"]
MINIO_URL = minio_config["MINIO_URL"]
ACCESS_KEY = minio_config["ACCESS_KEY"]
SECRET_KEY = minio_config["SECRET_KEY"]
BUCKET_NAME = minio_config["BUCKET_NAME"]

s3 = boto3.client(
    's3',
    endpoint_url=MINIO_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

class FileProcessingManager:

    @classmethod
    async def process(cls, pdf_url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    pdf_bytes = io.BytesIO(await response.read())
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to download PDF: {str(e)}")

        extracted_text = {}

        try:
            extracted_text = await cls.extract_text_from_pdf(pdf_bytes)
        except Exception as e:
            return json({"error": str(e)}, status=500)

        if not extracted_text.get(1):
            try:
                extracted_text = await cls.ocr_from_pdf(pdf_bytes)
            except Exception as e:
                return json({"error": str(e)}, status=500)

        if not extracted_text:
            return json({"error": "No text found in the PDF"}, status=400)

        file_name = f"uploads/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_url = await cls.upload_to_minio(pdf_bytes, file_name)

        return {"extracted_text": extracted_text, "file_url": file_url}

    @classmethod
    async def extract_text_from_pdf(cls, pdf_bytes):
        """
        Extracts text and bounding boxes from a PDF provided as a BytesIO object asynchronously.
        :param pdf_bytes: BytesIO object containing the PDF content
        :return: A dictionary with the page number as the key and a tuple of (text, bounding boxes) as the value
        """
        def extract():
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                text_and_bboxes = {}
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_and_bboxes[page_num + 1] = cls.get_text_and_bounding_boxes(page)
                return text_and_bboxes

        return await asyncio.to_thread(extract)

    @classmethod
    def get_text_and_bounding_boxes(cls, page):
        """
        Extract text and bounding boxes for each text block on the page.
        :param page: PyMuPDF page object
        :return: A list of tuples containing text and its bounding box (x0, y0, x1, y1)
        """
        blocks = page.get_text("dict")["blocks"]
        text_with_bboxes = []
        
        for block in blocks:
            if block["type"] == 0:  # type 0 is for text blocks
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]  # Bounding box in (x0, y0, x1, y1) format
                        text_with_bboxes.append({
                            "text": span["text"],
                            "bbox": bbox
                        })

        return text_with_bboxes

    @classmethod
    async def ocr_from_pdf(cls, pdf_bytes):
        """
        Perform OCR on a PDF provided as a BytesIO object asynchronously.
        Extracts both text and bounding boxes.
        :param pdf_bytes: BytesIO object containing the PDF content
        :return: A dictionary with page numbers as keys and a list of {text, bbox} dictionaries
        """
        images = await asyncio.to_thread(convert_from_bytes, pdf_bytes.getvalue())

        def extract_text_with_bboxes(image):
            """Extract text along with bounding boxes from an image using Tesseract OCR."""
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            ocr_results = []
            for i in range(len(data["text"])):
                if data["text"][i].strip():  # Ignore empty text
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    ocr_results.append({
                        "text": data["text"][i],
                        "bbox": [x, y, x + w, y + h]  # Convert width & height to x1, y1
                    })
            return ocr_results

        # Process each image in a separate thread
        text_results = await asyncio.gather(*[asyncio.to_thread(extract_text_with_bboxes, image) for image in images])

        return {page + 1: text_results[page] for page in range(len(text_results))}


    @classmethod
    async def upload_to_minio(cls, file_bytes, file_name):
        """Upload a file to MinIO using boto3 and return its URL"""
        try:
            try:
                s3.head_bucket(Bucket=BUCKET_NAME)
            except:
                s3.create_bucket(Bucket=BUCKET_NAME)

            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=file_name,
                Body=file_bytes,
                ContentType="application/pdf"
            )
            return f"http://localhost:9000/{BUCKET_NAME}/{file_name}"

        except NoCredentialsError as e:
            raise Exception(f"Credentials not found: {str(e)}")
        except Exception as e:
            raise Exception(f"Error uploading file to MinIO: {str(e)}")

    @classmethod
    async def get_total_pages(cls, pdf_bytes):
        """Get the total number of pages in a PDF"""
        def count_pages():
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                return doc.page_count

        return await asyncio.to_thread(count_pages)
