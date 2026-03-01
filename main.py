import os
import shutil
from datetime import datetime
from fastapi import FastAPI, Depends, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, schemas, database
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from fastapi import UploadFile, File, Form
import shutil
from fastapi import FastAPI, Depends, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, schemas, database
from fastapi import File, UploadFile
from datetime import datetime
from sqlalchemy import or_ 
from sqlalchemy.orm import joinedload

app = FastAPI(title="MediaVault Pro")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# Create the new tables
# This tells SQLAlchemy to create your tables if they don't exist

models.Base.metadata.create_all(bind=database.engine)

# 1. The Static Bridge (The one we just built!)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 2. THE DASHBOARD (The Face)
@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    search: str = None, 
    cat_id: int = None, 
    db: Session = Depends(database.get_db)
):
    # 1. Start the query and JOIN the Category table so we can search it
    query = db.query(models.DBMediaAsset).join(models.Category)
    
    # 2. Total count (before filtering)
    total_count = db.query(models.DBMediaAsset).count() 
    
    # 3. Smart Search: Look in Name, Location, AND Category Name
    if search:
        query = query.filter(
            or_(
                models.DBMediaAsset.name.contains(search),
                models.DBMediaAsset.location.contains(search),
                models.Category.name.contains(search) # This makes "AI Art" search work!
            )
        )
    
    # 4. Category Filter
    if cat_id:
        query = query.filter(models.DBMediaAsset.category_id == cat_id)
        
    # 5. Execute with proper ordering
    assets = query.order_by(models.DBMediaAsset.id.desc()).all()
    categories = db.query(models.Category).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "assets": assets, 
        "search_term": search,
        "categories": categories,
        "active_cat": cat_id,
        "total_count": total_count
    })

# 3. ADMIN: CREATE A COLLECTION (The Folder)
@app.post("/collections", tags=["Admin"])
def create_collection(col: schemas.CollectionBase, db: Session = Depends(database.get_db)):
    new_col = models.DBCollection(**col.model_dump())
    db.add(new_col)
    db.commit()
    return {"status": "Collection created!"}

# 4. ADMIN: ADD AN ASSET (The Button you were missing!)
@app.post("/collections/{collection_id}/assets", tags=["Admin"])
def add_asset(collection_id: int, asset: schemas.AssetBase, db: Session = Depends(database.get_db)):
    new_asset = models.DBMediaAsset(**asset.model_dump(), collection_id=collection_id)
    db.add(new_asset)
    db.commit()
    return {"status": "Asset added to the vault!"}

# Update your upload function arguments to include category_id
@app.post("/upload/")
async def upload(
    request: Request, 
    name: str = Form(...), 
    location: str = Form(None), 
    category_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # 1. GENERATE THE FILENAME FIRST
    filename = f"{datetime.now().timestamp()}_{file.filename}"
    
    # 2. SAVE THE ACTUAL FILE TO DISK
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. HANDLE THE OPTIONAL LOCATION
    final_location = location if location else "Digital/AI"

    # 4. SAVE TO DATABASE (Now 'filename' is defined!)
    new_asset = models.DBMediaAsset(
        name=name, 
        location=final_location, 
        file_path=filename, 
        category_id=category_id
    )
    
    db.add(new_asset)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/add-category/")
async def add_category(
    name: str = Form(...), 
    db: Session = Depends(database.get_db)
):
    # Check if category already exists
    existing = db.query(models.Category).filter(models.Category.name == name).first()
    if not existing:
        new_cat = models.Category(name=name)
        db.add(new_cat)
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
    