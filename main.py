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
from typing import List
from pydantic import BaseModel
from typing import List

app = FastAPI(title="MediaVault Pro")

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# Create the new tables
# This tells SQLAlchemy to create your tables if they don't exist

models.Base.metadata.create_all(bind=database.engine)

# 1. The Static Bridge 
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 2. THE DASHBOARD (The Face)
@app.get("/")
async def index(
    request: Request, 
    category_id: int = None, 
    search: str = None, 
    sort: str = "newest", # <--- Add this new parameter!
    db: Session = Depends(database.get_db)
):
    query = db.query(models.DBMediaAsset)

    # 1. Existing Filtering Logic
    if category_id:
        query = query.filter(models.DBMediaAsset.category_id == category_id)
    if search:
        query = query.filter(models.DBMediaAsset.name.contains(search))

    # 2. NEW Sorting Logic
    if sort == "newest":
        query = query.order_by(models.DBMediaAsset.id.desc())
    elif sort == "oldest":
        query = query.order_by(models.DBMediaAsset.id.asc())
    elif sort == "alphabetical":
        query = query.order_by(models.DBMediaAsset.name.asc())

    assets = query.all()
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "assets": assets, 
        "categories": categories,
        "current_sort": sort,        # Pass this back so the dropdown stays on the right choice
        "selected_category": category_id
    })

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

# Update your upload function arguments to include category_id
@app.post("/upload/")
async def upload(
    request: Request, 
    name: str = Form(...), 
    location: str = Form(None), 
    category_id: int = Form(...),
    files: List[UploadFile] = File(...), # <--- Change to List[UploadFile]
    db: Session = Depends(database.get_db)
):
    # 1. We now loop through EVERY file sent
    for file in files:
        # Generate a unique name for each file
        filename = f"{datetime.now().timestamp()}_{file.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Save the file to the folder
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Create a database entry for each file
        # We'll use the same Name/Location/Category for the whole batch
        new_asset = models.DBMediaAsset(
            name=name, 
            location=location if location else "Bulk Upload", 
            file_path=filename,
            category_id=category_id
        )
        db.add(new_asset)
    
    # 3. Commit everything at once at the end
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
    