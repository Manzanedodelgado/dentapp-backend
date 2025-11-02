from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.models.patient import PyObjectId


class AIConfigBase(BaseModel):
    knowledge_base: Dict[str, Any] = Field(default_factory=dict, description="Base de conocimientos dental")
    auto_responses: bool = Field(default=True, description="Activar respuestas automáticas")
    classification_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Reglas de clasificación")


class AIConfigCreate(AIConfigBase):
    pass


class AIConfigUpdate(BaseModel):
    knowledge_base: Optional[Dict[str, Any]] = None
    auto_responses: Optional[bool] = None
    classification_rules: Optional[List[Dict[str, Any]]] = None


class AIConfigInDB(AIConfigBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AIConfig(AIConfigInDB):
    pass


class AIResponse(BaseModel):
    """Respuesta del agente IA"""
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_classification: Optional[str] = None  # yellow, blue, green
    requires_human: bool = False
