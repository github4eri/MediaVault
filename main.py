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
from pydantic import BaseModel

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
    # 🕵️‍♂️ 1. Find the asset
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    
    if asset:
        # 📂 2. PHYSICAL DELETE: Remove the file from static/uploads
        file_path = os.path.join("static/uploads", asset.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"DEBUG: Deleted file {file_path}")

        # 🗑️ 3. DATABASE DELETE: Remove the record
        db.delete(asset)
        db.commit()
        print(f"DEBUG: Deleted asset {asset_id} from DB")

    return RedirectResponse(url="/", status_code=303)
    
#bulk delete
class BulkDeleteRequest(BaseModel):
    asset_ids: List[int]

@app.post("/bulk-delete")
async def bulk_delete(request: BulkDeleteRequest, db: Session = Depends(get_db)):
    try:
        # 🕵️‍♂️ Find all assets in the list
        assets = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id.in_(request.asset_ids)).all()
        
        for asset in assets:
            # Physical delete
            file_path = os.path.join("static/uploads", asset.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            # Database delete
            db.delete(asset)
            
        db.commit()
        return {"status": "success", "message": f"Deleted {len(assets)} assets"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

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
    
@app.post("/delete-category/{cat_id}")
async def delete_category(cat_id: int, db: Session = Depends(database.get_db)):
    # Find it in the vault
    category = db.query(models.Category).filter(models.Category.id == cat_id).first()
    if category:
        db.delete(category)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# 1. The "Edit Page" - This opens your edit.html
@app.get("/edit/{asset_id}")
async def edit_page(request: Request, asset_id: int, db: Session = Depends(database.get_db)):
    asset = database_ops.get_asset_by_id(db, asset_id)
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("edit.html", {
        "request": request, 
        "asset": asset, 
        "categories": categories
    })

# 2. The "Update Logic" - This saves the changes

@app.post("/edit/{asset_id}")
async def update_asset(
    asset_id: int, 
    name: str = Form(...), 
    ai_tags: str = Form(...),
    category_id: int = Form(...), 
    db: Session = Depends(database.get_db)
):
    # 1. Find the asset in the vault using the ID from the URL
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    
    if asset:
        # 🖊️ 2. Overwrite the old info with the new info from the form
        asset.name = name
        asset.ai_tags = ai_tags
        asset.category_id = category_id # 👈 And this line!
        
        # 🔒 3. Lock it in!
        db.commit()
        print(f"DEBUG: Asset {asset_id} updated successfully!")
    
    # 🏠 4. Send the user back to the dashboard to see the changes
    return RedirectResponse(url="/", status_code=303)


