from sqlalchemy.orm import Session
import models

def get_or_create_category(db: Session, cat_name: str):
    """Finds a category or creates it if missing."""
    cat = db.query(models.Category).filter(models.Category.name == cat_name).first()
    if not cat:
        cat = models.Category(name=cat_name)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat.id

def create_media_asset(db: Session, name, file_path, ai_tags, category_id):
    """Adds a new photo to the database 'cart'."""
    new_asset = models.DBMediaAsset(
        name=name,
        file_path=file_path,
        ai_tags=ai_tags,
        category_id=category_id
    )
    db.add(new_asset)

def get_asset_by_id(db: Session, asset_id: int):
    return db.query(models.DBMediaAsset).filter(models.DBMediaAsset.id == asset_id).first()
    



        