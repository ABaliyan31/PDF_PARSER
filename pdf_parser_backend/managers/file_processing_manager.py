import io
import boto3
from botocore.exceptions import NoCredentialsError
from sanic import json
from pdf2image import convert_from_bytes
import pytesseract
import aiohttp
import datetime
import fitz
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
    async def process(cls, pdf_url, page_number=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    pdf_bytes = io.BytesIO(await response.read())
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to download PDF: {str(e)}")

        extracted_text = {}
        total_pages = 0

        try:
            extracted_text, total_pages = await cls.extract_text_from_pdf(pdf_bytes, page_number)
        except Exception as e:
            return json({"error": str(e)}, status=500)

        if not extracted_text.get(page_number):
            try:
                extracted_text = await cls.ocr_from_pdf(pdf_bytes, page_number)
            except Exception as e:
                return json({"error": str(e)}, status=500)

        if not extracted_text:
            return json({"error": "No text found in the PDF"}, status=400)

        file_name = f"uploads/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_page_{page_number}.pdf" if page_number else f"uploads/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_url = await cls.upload_to_minio(pdf_bytes, file_name, page_number)

        return {
            "extracted_text": extracted_text,
            "file_url": file_url,
            "total_pages": total_pages
        }

    @classmethod
    async def extract_text_from_pdf(cls, pdf_bytes, page_number=None):
        """
        Extracts text from a PDF provided as a BytesIO object asynchronously.
        :param pdf_bytes: BytesIO object containing the PDF content
        :param page_number: Specific page to extract text from, None means all pages
        :return: A dictionary with the page number as the key and the text as the value
        """
        def extract():
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                total_pages = len(doc)
                if page_number:
                    page = doc.load_page(page_number - 1)  # Zero-based index
                    return {page_number: page.get_text()}, total_pages
                else:
                    return {page.number + 1: page.get_text() for page in doc}, total_pages

        return await asyncio.to_thread(extract)

    @classmethod
    async def ocr_from_pdf(cls, pdf_bytes, page_number=None):
        """
        Perform OCR on a PDF provided as a BytesIO object asynchronously.
        :param pdf_bytes: BytesIO object containing the PDF content
        :param page_number: Specific page to OCR, None means all pages
        :return: A dictionary with the page number as the key and the OCR-extracted text as the value
        """
        # Convert PDF pages to images
        images = await asyncio.to_thread(convert_from_bytes, pdf_bytes.getvalue())

        # If a page number is provided, we process only that page
        if page_number:
            image = images[page_number - 1]  # Zero-based index
            text = pytesseract.image_to_string(image)
            return {page_number: text}

        # Perform OCR on each image and gather the results for all pages
        text_results = await asyncio.gather(
            *[asyncio.to_thread(pytesseract.image_to_string, image) for image in images]
        )

        return {page + 1: text for page, text in enumerate(text_results)}

    @classmethod
    async def upload_to_minio(cls, pdf_bytes, file_name, page_number=None):
        """Upload a specific page of the PDF to MinIO using boto3 and return its URL"""
        try:
            try:
                s3.head_bucket(Bucket=BUCKET_NAME)
            except:
                s3.create_bucket(Bucket=BUCKET_NAME)

            # If a page number is provided, extract that page as a new PDF
            if page_number:
                with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                    page = doc.load_page(page_number - 1)
                    new_pdf = fitz.open()
                    new_pdf.insert_pdf(doc, from_page=page_number - 1, to_page=page_number - 1)
                    pdf_bytes = io.BytesIO(new_pdf.write())

            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=file_name,
                Body=pdf_bytes,
                ContentType="application/pdf"
            )

            return f"http://localhost:9000/{BUCKET_NAME}/{file_name}"

        except NoCredentialsError as e:
            raise Exception(f"Credentials not found: {str(e)}")
        except Exception as e:
            raise Exception(f"Error uploading file to MinIO: {str(e)}")
