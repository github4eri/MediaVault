from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from database import Base

class DBCollection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    is_published = Column(Boolean, default=False)
    
    assets = relationship("DBMediaAsset", back_populates="owner", cascade="all, delete-orphan")


# Add "Source" to your assets
class DBMediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    file_type = Column(String) 
    file_size_mb = Column(Float)
    camera_model = Column(String, default="Unknown")
    location = Column(String, default="Remote")
    resolution = Column(String, default="4K")
    
    # --- NEW: SOURCE TYPE ---
    # Options: "Camera", "AI", "Hybrid"
    source_type = Column(String, default="Camera") 

    collection_id = Column(Integer, ForeignKey("collections.id"))
    owner = relationship("DBCollection", back_populates="assets")
    