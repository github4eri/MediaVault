from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean  
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # This connects the category to its assets
    assets = relationship("DBMediaAsset", back_populates="category")

class SubcategoryGroup(Base):
    __tablename__ = "subcategory_groups"
    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    options = relationship("SubcategoryOption", back_populates="group", cascade="all, delete-orphan")

class SubcategoryOption(Base):
    __tablename__ = "subcategory_options"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String, index=True)
    group_id = Column(Integer, ForeignKey("subcategory_groups.id"))
    group    = relationship("SubcategoryGroup", back_populates="options")

class DBMediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    file_path = Column(String)
    location = Column(String)
    ai_tags = Column(String, nullable=True)
    original_file_path = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="assets")
    copyright_option_id   = Column(Integer, ForeignKey("subcategory_options.id"), nullable=True)
    use_purpose_option_id = Column(Integer, ForeignKey("subcategory_options.id"), nullable=True)
    copyright_option   = relationship("SubcategoryOption", foreign_keys=[copyright_option_id])
    use_purpose_option = relationship("SubcategoryOption", foreign_keys=[use_purpose_option_id])

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String) # 🔒 never store the plain password!
    is_active = Column(Boolean, default=True)    