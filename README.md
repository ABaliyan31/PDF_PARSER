go inside the PDF_PARSER folder and run the following commands(make sure docker is running on your machine)
inside config.json in backend folder add the following config:

{
    "APP_NAME": "PDF_Transcriber",
    "MINIO": {
        "MINIO_URL": "http://minio:9000",
        "ACCESS_KEY": "minioadmin",
        "SECRET_KEY": "minioadmin",
        "BUCKET_NAME": "pdf-bucket"
    }
}

docker-compose build
docker-compose up
