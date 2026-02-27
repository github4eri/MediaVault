from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    # This connects the category to its assets
    assets = relationship("DBMediaAsset", back_populates="category")

class DBMediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)
    file_path = Column(String) # <--- ADD THIS LINE!
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    category = relationship("Category", back_populates="assets")
    