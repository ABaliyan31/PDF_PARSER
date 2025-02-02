from sanic import Blueprint, Request, json
from managers.file_processing_manager  import FileProcessingManager

pdf_parser_blueprint = Blueprint("pdf_parser_blueprint")



@pdf_parser_blueprint.route("/extract_text_from_pdf", methods=["POST"])
async def parse_pdf(request: Request):
    pdf_url = request.json.get("pdf_url")
    page = request.json.get("page", None)
    if not pdf_url:
        return json({"error": "No PDF URL provided"}, status=400)
    data = await FileProcessingManager.process(pdf_url, page)   
    return json(data)

