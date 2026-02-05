from pydantic import BaseModel, Field
from typing import Literal, Dict, Optional

class Entity(BaseModel):
    """实体模型"""
    entity_id: Optional[str] = None
    type: Literal["person", "project", "event", "location", "concept"]
    name: str = Field(..., min_length=1, max_length=100)
    attributes: Dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0, le=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "person",
                "name": "张三",
                "attributes": {"role": "同事", "department": "技术部"},
                "confidence": 0.9
            }
        }
