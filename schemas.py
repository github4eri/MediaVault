from pydantic import BaseModel
from typing import List, Optional

class AssetBase(BaseModel):
    filename: str
    file_type: str
    file_size_mb: float
    camera_model: Optional[str] = "Unknown"
    location: Optional[str] = "Remote"
    resolution: Optional[str] = "4K"
    source_type: Optional[str] = "Camera" # Add this!

class AssetPublic(AssetBase):
    id: int
    class Config:
        from_attributes = True

class CollectionBase(BaseModel):
    name: str
    description: str
    is_published: bool = False

class CollectionPublic(CollectionBase):
    id: int
    assets: List[AssetPublic] = []
    class Config:
        from_attributes = True

