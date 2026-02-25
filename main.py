from fastapi import UploadFile, File, Form
import shutil
import os
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse
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
async def read_dashboard(request: Request, search: str = None, db: Session = Depends(database.get_db)):
    query = db.query(models.DBMediaAsset).order_by(models.DBMediaAsset.id.desc())
    
    if search:
        query = query.filter(models.DBMediaAsset.name.ilike(f"%{search}%"))
    
    assets = query.all()
    # THE NEW LINE:
    total_assets = len(assets)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "assets": assets, 
        "total_count": total_assets, # ADD THIS
        "search_term": search
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

@app.post("/upload/")
async def upload_asset(
    name: str = Form(...),
    source: str = Form(...),
    location: str = Form(None),
    camera_model: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # --- Everything for UPLOAD must be indented under here ---
    os.makedirs("static/uploads", exist_ok=True)
    
    file_location = f"static/uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_asset = models.DBMediaAsset(
        name=name,
        source=source,
        location=location,
        camera_model=camera_model,
        file_path=file.filename,
        collection_id=1 
    )
    db.add(new_asset)
    db.commit()
    
    from fastapi.responses import RedirectResponse
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
