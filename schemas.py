from pydantic import BaseModel
from typing import List, Optional


class AssetBase(BaseModel):
    name: str
    source: str
    location: Optional[str] = None
    camera_model: Optional[str] = None
    file_path: Optional[str] = None # Make sure this is here!

class AssetPublic(AssetBase):
    id: int
    class Config:
        from_attributes = True

class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_published: bool = False # Add this!

class CollectionPublic(CollectionBase):
    id: int
    assets: List[AssetPublic] = []
    class Config:
        from_attributes = True

