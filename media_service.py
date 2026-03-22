import os
import vision
import database_ops
from sqlalchemy.orm import Session

def handle_upload_process(db: Session, file, category_name: str, asset_title: str):
    """Handles saving, AI analysis, and DB registration."""
    # 📂 1. Save the Physical File
    upload_folder = "static/uploads"
    file_path = os.path.join(upload_folder, file.filename)
    
    with open(file_path, "wb+") as file_object:
        file_object.write(file.file.read())

    # 🧠 2. Get AI Tags (using our vision specialist)
    try:
        ai_description = vision.analyze_media(file_path) 
    except Exception as e:
        print(f"DEBUG: AI Routing Error - {e}")
        ai_description = "AI-Analysis-Unavailable"

    # 🗄️ 3. Register in Database (FIXED: Using asset_title!)
    cat_id = database_ops.get_or_create_category(db, category_name)
    database_ops.create_asset(
        db=db, 
        name=asset_title,        # ✨ Use the title you typed!
        file_path=file.filename, 
        ai_tags=ai_description, 
        category_id=cat_id
    )
    return True
    
