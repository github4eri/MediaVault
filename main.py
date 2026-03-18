import os
import uuid
import shutil
import zipfile
import io
from typing import List
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, Body
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# --- INTERNAL COMPONENTS ---
import models
import database
import vision        # The Brain
import database_ops  # The Clerk
from database import engine, SessionLocal

# --- INITIALIZATION ---
load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediaVault Pro")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    assets = db.query(models.DBMediaAsset).all()
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "assets": assets, 
        "categories": categories
    })

# --- 2. UPLOAD & AI ---
@app.post("/upload/")
async def upload(
    request: Request, 
    files: List[UploadFile] = File(...), 
    name: str = Form(...), 
    category_name: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Ask the Clerk for the Category ID
    cat_id = database_ops.get_or_create_category(db, category_name)

    for file in files:
        file_ext = os.path.splitext(file.filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex}{file_ext}"
        save_path = os.path.join("static/uploads", unique_name)
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ask the Brain for Tags
        tags = vision.get_tags(save_path)

        # Ask the Clerk to prepare the database entry
        database_ops.create_media_asset(db, name, unique_name, tags, cat_id)

    db.commit() # Save everything!
    return RedirectResponse(url="/", status_code=303)

# --- 3. EDIT & DELETE ---
@app.post("/edit")
async def edit_asset(
    id: int = Form(...), 
    name: str = Form(...), 
    ai_tags: str = Form(None), 
    db: Session = Depends(get_db)
):
    db_asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == id).first()
    if db_asset:
        db_asset.name = name
        db_asset.ai_tags = ai_tags
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{asset_id}")
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    if asset:
        # Remove physical file
        file_path = os.path.join("static/uploads", asset.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.delete(asset)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- 4. CATEGORIES ---
@app.post("/add-category")
async def add_category(name: str = Form(...), db: Session = Depends(get_db)):
    database_ops.get_or_create_category(db, name)
    return RedirectResponse(url="/", status_code=303)

# --- 5. EXPORT / BULK (Special Tools) ---
@app.get("/export-vault")
async def export_vault(db: Session = Depends(get_db)):
    assets = db.query(models.DBMediaAsset).all()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for asset in assets:
            file_path = f"static/uploads/{asset.file_path}"
            if os.path.exists(file_path):
                zip_file.write(file_path, arcname=asset.name + os.path.splitext(asset.file_path)[1])
    zip_buffer.seek(0)
    return StreamingResponse(zip_buffer, media_type="application/zip", 
                             headers={"Content-Disposition": "attachment; filename=vault_export.zip"})

# --- STARTUP TASKS ---
@app.on_event("startup")
def startup_tasks():
    db = SessionLocal()
    # Check if categories exist, create if not (Photography, AI Art, etc.)
    if not db.query(models.Category).first():
        db.add_all([models.Category(name="Photography"), models.Category(name="AI Art")])
        db.commit()
    db.close()
    
