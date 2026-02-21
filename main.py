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
def read_dashboard(request: Request, db: Session = Depends(database.get_db)):
    collections = db.query(models.DBCollection).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "collections": collections})

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
