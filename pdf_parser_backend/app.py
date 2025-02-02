from routes.extract_text_pdf import pdf_parser_blueprint
from sanic import Sanic
from sanic_ext import Extend
import json
from config import config


app = Sanic(config["APP_NAME"])
app.blueprint(pdf_parser_blueprint)
Extend(app)

@app.middleware("response")
async def cors_middleware(request, response):
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Credentials"] = "true"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, workers=4)
