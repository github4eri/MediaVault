from fastapi import UploadFile, File, Form
import shutil
import os
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, schemas, database

# Create the new tables
# This tells SQLAlchemy to create your tables if they don't exist
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="MediaVault Pro")

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
    query = db.query(models.DBMediaAsset)
    
    # 1. Total count (for the stats bar)
    total_count = query.count() # <--- MAKE SURE THIS LINE IS HERE
    
    if search:
        query = query.filter(models.DBMediaAsset.name.contains(search))
    
    if cat_id:
        query = query.filter(models.DBMediaAsset.category_id == cat_id)
        
    assets = query.order_by(models.DBMediaAsset.id.desc()).all()
    categories = db.query(models.Category).all()
    
    # 2. Add total_count to the dictionary below
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "assets": assets, 
        "search_term": search,
        "categories": categories,
        "active_cat": cat_id,
        "total_count": total_count # <--- AND THIS LINE!
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
async def create_upload(
    name: str = Form(...),
    source: str = Form(...),
    location: str = Form(None),      # Changed (...) to (None) to make it optional
    camera_model: str = Form(None),  # Changed (...) to (None) to make it optional
    category_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # ... rest of your code
    # Save file logic remains the same...
    file_path = file.filename 
    # (Make sure your file saving code is still here)

    new_asset = models.DBMediaAsset(
        name=name,
        file_path=file_path,
        source=source,
        location=location,
        camera_model=camera_model,
        category_id=category_id # ADD THIS LINE
    )
    db.add(new_asset)
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
    # Check if categories exist, if not, create them
    if not db.query(models.Category).first():
        cat1 = models.Category(name="AI Art")
        cat2 = models.Category(name="Photography")
        cat3 = models.Category(name="Videos")
        db.add_all([cat1, cat2, cat3])
        db.commit()
    db.close()

