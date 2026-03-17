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
    file_path = Column(String)
    location = Column(String)
    
    # 🎯 USE ONLY THIS ONE. Remove the line that says 'tags = ...'
    ai_tags = Column(String, nullable=True) 
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="assets")
    