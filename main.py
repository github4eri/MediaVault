from sqlalchemy import or_
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import engine, get_db

# Create the new tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediaVault Pro")

# --- NEW: Tell FastAPI where your HTML files live ---
templates = Jinja2Templates(directory="templates")

ADMIN_SECRET_KEY = "MediaPass123" # Updated the key!

def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")
    return x_admin_key

# 2. The Customer Route

@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
def read_dashboard(request: Request, db: Session = Depends(get_db), search: str = None):
    query = db.query(models.DBCollection)
    
    if search:
        # This is the "Smart Filter": It checks the Collection Name 
        # OR searches inside the linked Assets for a matching Camera Model
        query = query.join(models.DBMediaAsset).filter(
            or_(
                models.DBCollection.name.contains(search),
                models.DBMediaAsset.camera_model.contains(search),
                models.DBMediaAsset.location.contains(search)
            )
        ).distinct() # .distinct() prevents the same project from showing twice
    
    collections = query.all()
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "collections": collections, "search_term": search}
    )

#3. Admin Route
# 1. CREATE A COLLECTION (The "Project" Folder)
@app.post("/collections", dependencies=[Depends(verify_admin)], tags=["Admin Panel"])
def create_collection(item: schemas.CollectionBase, db: Session = Depends(get_db)):
    new_collection = models.DBCollection(**item.model_dump())
    db.add(new_collection)
    db.commit()
    return {"status": "Collection created!"}

# 2. ADD A MEDIA ASSET (The actual Photos/Videos)
@app.post("/collections/{collection_id}/assets", dependencies=[Depends(verify_admin)], tags=["Admin Panel"])
def add_asset(collection_id: int, asset: schemas.AssetBase, db: Session = Depends(get_db)):
    # Look for the collection folder first
    collection = db.query(models.DBCollection).filter(models.DBCollection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found!")

    # Create the asset linked to that collection
    new_asset = models.DBMediaAsset(**asset.model_dump(), collection_id=collection_id)
    db.add(new_asset)
    db.commit()
    return {"status": f"Successfully added {asset.filename} to {collection.name}!"}

        # 1. CREATE A COLLECTION (The "Project" Folder)
# NEW VERSION
@app.post("/collections/", response_model=schemas.CollectionPublic)
def create_collection(collection: schemas.CollectionBase, db: Session = Depends(get_db)): # <--- Changed here
    new_col = models.DBCollection(**collection.dict())
    db.add(new_col)
    db.commit()
    db.refresh(new_col)
    return new_col
    new_collection = models.DBCollection(**item.model_dump())
    db.add(new_collection)
    db.commit()
    return {"status": "Collection created!"}

        # 2. ADD A MEDIA ASSET (The actual Photos/Videos)
@app.post("/collections/{collection_id}/assets", dependencies=[Depends(verify_admin)], tags=["Admin Panel"])
def add_asset(collection_id: int, asset: schemas.AssetBase, db: Session = Depends(get_db)):
    # Look for the collection folder first
    collection = db.query(models.DBCollection).filter(models.DBCollection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found!")

    # Create the asset linked to that collection
    new_asset = models.DBMediaAsset(**asset.model_dump(), collection_id=collection_id)
    db.add(new_asset)
    db.commit()
    return {"status": f"Successfully added {asset.filename} to {collection.name}!"}

# --- ADMIN DELETE ROUTES ---

@app.delete("/assets/{asset_id}", dependencies=[Depends(verify_admin)], tags=["Admin Panel"])
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    db.delete(asset)
    db.commit()
    return {"status": f"Deleted asset {asset_id}"}

@app.delete("/collections/{collection_id}", dependencies=[Depends(verify_admin)], tags=["Admin Panel"])
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = db.query(models.DBCollection).filter(models.DBCollection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # This deletes the collection and all its assets (thanks to our 'cascade' setup)
    db.delete(collection)
    db.commit()
    return {"status": "Collection and all associated assets deleted"}
    