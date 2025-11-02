from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.patient import PyObjectId


class ConversationBase(BaseModel):
    patient_id: Optional[str] = Field(None, description="ID del paciente si está registrado")
    whatsapp_number: str = Field(..., description="Número de WhatsApp del paciente")
    status: str = Field(default="gray", description="yellow (urgente), blue (normal), green (resuelta), gray (sin clasificar)")
    last_message_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    patient_id: Optional[str] = None
    status: Optional[str] = Field(None, description="yellow, blue, green, gray")
    last_message_at: Optional[datetime] = None


class ConversationInDB(ConversationBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "patient_id": "507f1f77bcf86cd799439011",
                "whatsapp_number": "664123456",
                "status": "yellow",
                "last_message_at": "2025-10-31T14:30:00"
            }
        }


class Conversation(ConversationInDB):
    pass
