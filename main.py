from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import json

from utils.text_extractor import text_extractor
from ai_tasks.document_analyzer import DocumentAnalyzer

app = FastAPI()


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def handle_upload(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    email: str = Form(...)
):
    upload_path = BASE_DIR / "static" / file.filename
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Step 1: Extract text
    text = text_extractor(upload_path)

    
    document_analyzer = DocumentAnalyzer()

    result = await document_analyzer.analyze_document(document_text=text,user_legal_name=name)


    del document_analyzer
    
    return templates.TemplateResponse("result.html", {"request": request, "result": result})
