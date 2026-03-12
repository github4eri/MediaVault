from google import genai  #new
from fastapi import FastAPI, Request, Depends, Form  
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session                   
from database import SessionLocal, engine           
import models
import os
import shutil
from datetime import datetime
from fastapi import File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import schemas, database
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from typing import List
from pydantic import BaseModel
import zipfile
import io
from fastapi.responses import StreamingResponse
from PIL import Image 
from dotenv import load_dotenv 
import uuid

# The client will automatically look for the GEMINI_API_KEY 
client = genai.Client()

load_dotenv() # This searches for the .env file
api_key = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: My API key is found: {api_key is not None}")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={'api_version': 'v1'})

app = FastAPI(title="MediaVault Pro")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# Create the new tables
# This tells SQLAlchemy to create your tables if they don't exist

models.Base.metadata.create_all(bind=database.engine)

# This creates a fresh database session for every request
def get_db():
    db = SessionLocal() # This must match whatever you named your sessionmaker
    try:
        yield db
    finally:
        db.close()

# 1. The Static Bridge 
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 2. THE DASHBOARD (The Face)

@app.get("/")
async def index(
    request: Request, 
    search: str = None, 
    category_id: int = None, # 👈 Matches your HTML: /?category_id=...
    db: Session = Depends(database.get_db)
):
    # 1. Get categories for the top bar
    categories = db.query(models.Category).all()
    
    # 2. Start the query for assets
    query = db.query(models.DBMediaAsset)

    # 3. Apply Search Filter
    if search:
        query = query.filter(
            (models.DBMediaAsset.name.contains(search)) | 
            (models.DBMediaAsset.ai_tags.contains(search))
        )

    # 4. Apply Category Filter
    if category_id:
        query = query.filter(models.DBMediaAsset.category_id == category_id)

    # 5. Execute and Sort
    assets = query.order_by(models.DBMediaAsset.id.desc()).all()
    
    return templates.TemplateResponse("dashboard.html", {
    "request": request, 
    "assets": assets, 
    "categories": categories,
    "active_cat": category_id, # 👈 MUST match this name!
    "total_count": len(assets)
})

#Add category
@app.post("/add-category")
async def add_category(name: str = Form(...), db: Session = Depends(database.get_db)):
    new_cat = models.Category(name=name)
    db.add(new_cat)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

# 3Grouping the Edit route with your other Admin tasks
@app.post("/edit/{asset_id}", tags=["Admin"]) 
async def edit_asset(
    asset_id: int, 
    new_name: str = Form(...), 
    new_location: str = Form(None),
    new_category_id: int = Form(...), # <--- ADD THIS LINE
    db: Session = Depends(database.get_db)
):
    # 1. Find the specific photo by its ID
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    
    if asset:
        # 2. Update the fields with the new info from the form
        asset.name = new_name
        asset.location = new_location
        asset.category_id = new_category_id # <--- ADD THIS LINE
        
        # 3. Save to the database
        db.commit()
    
    # 4. Send the user back to the dashboard to see the changes
    return RedirectResponse(url="/", status_code=303)

#4 ADMIN: CREATE A COLLECTION (The Folder)
@app.post("/collections", tags=["Admin"])
def create_collection(col: schemas.CollectionBase, db: Session = Depends(database.get_db)):
    new_col = models.DBCollection(**col.model_dump())
    db.add(new_col)
    db.commit()
    return {"status": "Collection created!"}

# 5. ADMIN: ADD AN ASSET (The Button you were missing!)
@app.post("/collections/{collection_id}/assets", tags=["Admin"])
def add_asset(collection_id: int, asset: schemas.AssetBase, db: Session = Depends(database.get_db)):
    new_asset = models.DBMediaAsset(**asset.model_dump(), collection_id=collection_id)
    db.add(new_asset)
    db.commit()
    return {"status": "Asset added to the vault!"}

# Update upload function arguments to include category_id
@app.post("/upload/")
async def upload(
    request: Request, 
    files: List[UploadFile] = File(...), 
    name: str = Form(...), 
    location: str = Form(None), 
    category_id: int = Form(...), # 👈 This matches HTML dropdown
    db: Session = Depends(database.get_db)
):
    for file in files:
        # 1. Start with a default "Safety" value
        ai_tags = "no tags"
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        save_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Only attempt AI analysis if it's an image 🖼️
        if file_extension in [".jpg", ".jpeg", ".png", ".webp"]:
            try:
                # 🖼️ open the image and send it to the new client
                from PIL import Image
                img = Image.open(save_path)
                
                # New "Modern" call syntax:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=["Describe this image with 3 to 5 simple comma-separated tags.", img]
                )
                
                ai_tags = response.text.strip().lower()
            except Exception as e:
                print(f"DEBUG: AI Vision failed: {e}")
                # Note: ai_tags remains "no tags", so the database save won't crash!
                        
        # --- C. Save to Database (Including ai_tags!) ---
        new_asset = models.DBMediaAsset(
            name=name,
            file_path=file.filename, 
            ai_tags=ai_tags,
            location=location,
            category_id=category_id
        )
        db.add(new_asset)
    
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete-category/{cat_id}")
async def delete_category(
    cat_id: int, 
    db: Session = Depends(database.get_db)
):
    category = db.query(models.Category).filter(models.Category.id == cat_id).first()
    if category:
        db.delete(category)
        db.commit()
    return RedirectResponse(url="/", status_code=303)
    
# --- NOW we start a brand new "island" for DELETE ---
@app.post("/delete/{asset_id}")
async def delete_asset(asset_id: int, db: Session = Depends(database.get_db)):
    db_asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    
    if db_asset:
        db.delete(db_asset)
        db.commit()
        
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=303)

class BulkDeleteRequest(BaseModel):
    asset_ids: List[int]

@app.post("/bulk-delete")
async def bulk_delete(request: BulkDeleteRequest, db: Session = Depends(database.get_db)):
    # Delete all assets whose ID is in the list we just sent
    db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id.in_(request.asset_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": "Successfully deleted items"}

@app.on_event("startup")
def startup_populate_categories():
    db = database.SessionLocal()
# THE PURGE: This clears out the 'ghost' assets
    db.query(models.DBMediaAsset).delete()

    # Check if categories exist, if not, create them
    if not db.query(models.Category).first():
        cat1 = models.Category(name="AI Art")
        cat2 = models.Category(name="Photography")
        cat3 = models.Category(name="Videos")
        db.add_all([cat1, cat2, cat3])
        db.commit()
    db.close()

@app.get("/delete/{asset_id}")
async def delete_asset(
    asset_id: int, 
    db: Session = Depends(database.get_db)
):
    # 1. Find the asset in the database
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    
    if asset:
        # 2. DELETE THE ACTUAL FILE from your computer
        file_path = os.path.join("static/uploads", asset.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 3. DELETE THE RECORD from the database
        db.delete(asset)
        db.commit()
    
    # 4. Redirect back to the home page
    return RedirectResponse(url="/", status_code=303)
    
@app.post("/import-zip")
async def import_zip(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith('.zip'):
        return {"error": "Please upload a .zip file"}

    # 1. Read the uploaded zip into memory
    contents = await file.read()
    zip_buffer = io.BytesIO(contents)

    with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
        # 2. Loop through every file inside the zip
        for file_info in zip_ref.infolist():
            if file_info.is_dir(): continue # Skip folders
            
            # 3. Save the file to your static/uploads folder
            filename = file_info.filename
            with zip_ref.open(filename) as source, open(f"static/uploads/{filename}", "wb") as target:
                target.write(source.read())

            # 4. Add to Database
            new_asset = models.DBMediaAsset(
                name=filename,
                file_path=filename,
                location="Bulk Import",
                category_id=1 # To make sure you have at least one category in DB.
            )
            db.add(new_asset)
    
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/export-vault")
async def export_vault(db: Session = Depends(database.get_db)):
    # 1. Get all the assets you've uploaded
    assets = db.query(models.DBMediaAsset).all()
    
    # 2. Create a "virtual file" in the computer's memory (RAM)
    # This is much faster than writing a file to the hard drive!
    zip_buffer = io.BytesIO()
    
    # 3. Start packing the zip file
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for asset in assets:
            file_path = f"static/uploads/{asset.file_path}"
            if os.path.exists(file_path):
                # We use asset.name so the files inside the zip have nice names
                # like "Sunset.jpg" instead of "12345_uuid.jpg"
                zip_file.write(file_path, arcname=asset.name)
                
    # 4. "Rewind" the virtual file to the beginning so we can send it
    zip_buffer.seek(0)
    
    # 5. Send it to the browser as a download
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=my_media_vault.zip"}
    )   
