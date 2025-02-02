import io
import boto3
from botocore.exceptions import NoCredentialsError
from sanic import json
from pdf2image import convert_from_bytes
import pytesseract
import aiohttp
import io
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

        values = " ".join(extracted_text.values())
        if not values:
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
        Extracts text from a PDF provided as a BytesIO object asynchronously.
        :param pdf_bytes: BytesIO object containing the PDF content
        :return: A dictionary with the page number as the key and the text as the value
        """
        def extract():
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                return {page.number + 1: page.get_text() for page in doc}

        return await asyncio.to_thread(extract)


    @classmethod
    async def ocr_from_pdf(cls, pdf_bytes):
        """
        Perform OCR on a PDF provided as a BytesIO object asynchronously.
        :param pdf_bytes: BytesIO object containing the PDF content
        :return: A dictionary with the page number as the key and the OCR-extracted text as the value
        """
        # Convert PDF pages to images
        images = await asyncio.to_thread(convert_from_bytes, pdf_bytes.getvalue())

        # Perform OCR on each image and gather the results
        text_results = await asyncio.gather(
            *[asyncio.to_thread(pytesseract.image_to_string, image) for image in images]
        )

        # Create a dictionary with the page number as the key and the OCR text as the value
        return {page + 1: text for page, text in enumerate(text_results)}


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