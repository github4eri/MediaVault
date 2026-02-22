from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

from sqlalchemy import Column, Integer, String, Boolean # Add Boolean here!

class DBCollection(Base):
    __tablename__ = "collections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    is_published = Column(Boolean, default=False) # Add this!
    
    assets = relationship("DBMediaAsset", back_populates="collection")
    
    # HANDSHAKE PART A: 
    # This says "Look for a variable named 'collection' inside DBMediaAsset"
    assets = relationship("DBMediaAsset", back_populates="collection")

class DBMediaAsset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    file_path = Column(String)
    source = Column(String)
    location = Column(String)
    camera_model = Column(String)
    file_size = Column(Float, nullable=True)
    resolution = Column(String, nullable=True)
    collection_id = Column(Integer, ForeignKey("collections.id"))

    # HANDSHAKE PART B: 
    # This variable MUST be named 'collection' because Part A is looking for it!
    # And it says "Look for a variable named 'assets' inside DBCollection"
    collection = relationship("DBCollection", back_populates="assets")
