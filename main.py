import os
import uuid
import shutil
import zipfile
import io
from typing import List
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload
from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, Body
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
from fastapi.responses import FileResponse
from datetime import datetime
from google import genai

# --- INTERNAL COMPONENTS ---
import models
import database
import database_ops  # The Clerk
from database import engine, SessionLocal
from pydantic import BaseModel
import vision
from fastapi import Response 
import security # security.py is imported
from fastapi import Cookie
import media_service

# 🛡️ THE FOLDER SHIELD: Create these before the app starts
os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)

# 🚦 THE RULES (Global Constants) and for security
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "mp4"}


# --- INITIALIZATION ---
load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediaVault Pro")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# 🛡️ THE CACHE SHIELD: Prevents the Python 3.14 "unhashable" error
templates.env.cache = None

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 1. DASHBOARD ---
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="login.html"
)

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(database.get_db)
):
    # 🕵️‍♂️ What did the user type?
    print(f"DEBUG: Attempting login for user: '{username}'")

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        # 🕵️‍♂️ Did we even find the user?
        print(f"DEBUG: User '{username}' NOT found in database.")
        
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Invalid username"}
        )
        
    # 🕵️‍♂️ Compare the keys
    is_valid = security.verify_password(password, user.hashed_password)
    print(f"DEBUG: Password match result: {is_valid}")

    if not is_valid:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid password"})

 
    # 🕵️‍♂️ 1. Find the user in the database
    user = db.query(models.User).filter(models.User.username == username).first()

    # 🕵️‍♂️ 2. Check if user exists AND if the password is correct
    if not user or not security.verify_password(password, user.hashed_password):
        # If wrong, send them back to login with an error message
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid username or password"
        })

    # 🕵️‍♂️ 3. If correct, "Lock the Door" by setting a simple Cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="is_logged_in", value="true") # This is our temporary "Key Card"
    return response

@app.get("/")
async def dashboard(
    request: Request, 
    search: str = None,           # 🔍 Captures search text
    category: int = None,         # 📁 Captures category ID
    db: Session = Depends(get_db), # 🔑 Use the local get_db
    is_logged_in: str = Cookie(None)
):
    # 🚫 1. SECURITY CHECK: If not logged in, go to login page
    if is_logged_in != "true":
        return RedirectResponse(url="/login", status_code=303)

    # 🏗️ 2. BASE QUERY: Start with all assets
    query = db.query(models.DBMediaAsset)

    # 🔍 3. SEARCH FILTER: If user typed something
    if search:
        query = query.filter(
            (models.DBMediaAsset.name.ilike(f"%{search}%")) | 
            (models.DBMediaAsset.ai_tags.ilike(f"%{search}%"))
        )
    
    # 📁 4. CATEGORY FILTER: If user clicked a category
    if category:
        query = query.filter(models.DBMediaAsset.category_id == category)

    # 🚀 5. EXECUTE & RENDER
    assets = query.all()
    categories = db.query(models.Category).all()

    return templates.TemplateResponse(
    request=request, 
    name="dashboard.html", 
    context={"assets": assets, "categories": categories}
)


# --- THE UPLOAD & AI ROUTE ---
@app.post("/upload/")
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    asset_title: str = Form(...),     # 👈 Add this: Get the Title from the form!
    category_name: str = Form(...),
    db: Session = Depends(database.get_db),
    is_logged_in: str = Cookie(None)
):
    # 🚫 Only logged-in users can upload
    if is_logged_in != "true":
        raise HTTPException(status_code=401, detail="Please login first")

    # 🕵️‍♂️ 1. Extension Guard
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "mp4"}
    file_ext = file.filename.split(".")[-1].lower()
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file.")

    # 🚀 2. Hand off to the Manager
    # This one line replaces all the code you were repeating!
    media_service.handle_upload_process(db, file, category_name, asset_title)

    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    # 🗑️ Delete the "Key Card"
    response.delete_cookie("is_logged_in")
    return response

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
async def export_vault_data():
    filename = f"vault_export_{datetime.now().strftime('%Y%m%d')}.csv"
    os.makedirs("exports", exist_ok=True)
    filepath = os.path.join("exports", filename)

    db = SessionLocal()
    try:
        # 🚀 THE FIX: 'joinedload' grabs the category data while the session is still open
        assets = db.query(models.DBMediaAsset).options(
            joinedload(models.DBMediaAsset.category)
        ).all()

        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Location", "AI Tags", "Category", "File Path"])
            
            for item in assets:
                # Now item.category.name will work because we pre-loaded it!
                category_name = item.category.name if item.category else "No Category"
                
                writer.writerow([
                    item.id, 
                    item.name, 
                    item.location, 
                    item.ai_tags, 
                    category_name, 
                    item.file_path
                ])
    finally:
        db.close() # 🔒 close the session AFTER the loop is done

    return FileResponse(path=filepath, filename=filename, media_type='text/csv')

# --- STARTUP TASKS ---
@app.on_event("startup")
def startup_tasks():
    db = SessionLocal()
    try:
        # 1. Create categories if they don't exist
        if not db.query(models.Category).first():
            db.add_all([models.Category(name="Photography"), models.Category(name="AI Art")])
            db.commit()
        
        # 2. Create admin if it doesn't exist
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            from security import get_password_hash
            # 💡 TIP: Make sure your password here isn't actually super long!
            new_user = models.User(
                username="admin", 
                hashed_password=get_password_hash("admin123") # Change this later!
            )
            db.add(new_user)
            db.commit()
            print("DEBUG: Admin user created successfully!")
    except Exception as e:
        print(f"ERROR during startup: {e}")
    finally:
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
    return templates.TemplateResponse(
    request=request, 
    name="edit.html", 
    context={"asset": asset, "categories": categories}
)

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

@app.get("/maintenance/cleanup")
async def cleanup_orphaned_files(db: Session = Depends(database.get_db)):
    # 1. Get all file names currently in the Database
    db_files = [asset.file_path for asset in db.query(models.DBMediaAsset).all()]
    
    # 2. Get all file names currently in the Folder
    upload_folder = "static/uploads"
    folder_files = os.listdir(upload_folder)
    
    deleted_count = 0
    for file_name in folder_files:
        # If the file is in the folder but NOT in the database...
        if file_name not in db_files and file_name != ".gitignore":
            file_path = os.path.join(upload_folder, file_name)
            try:
                os.remove(file_path) # 🗑️ Delete it!
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_name}: {e}")
                
    return {"status": "success", "message": f"Cleaned up {deleted_count} orphaned files."}

