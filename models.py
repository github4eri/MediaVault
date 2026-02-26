from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

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
    source = Column(String)
    location = Column(String)
    camera_model = Column(String)
    # If you have a 'price' or 'size' field using Float, it goes here:
    # file_size = Column(Float) 

    # Link this asset to a category
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="assets")
    