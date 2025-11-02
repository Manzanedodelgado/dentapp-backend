from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.patient import PyObjectId


class MessageBase(BaseModel):
    conversation_id: str = Field(..., description="ID de la conversación")
    type: str = Field(default="text", description="text, button, template")
    content: str = Field(..., min_length=1)
    sender: str = Field(..., description="patient, clinic, ai")
    sent_at: datetime = Field(default_factory=datetime.utcnow)


class MessageCreate(MessageBase):
    pass


class MessageInDB(MessageBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "type": "text",
                "content": "Hola, ¿cuánto cuesta una limpieza?",
                "sender": "patient",
                "sent_at": "2025-10-31T14:30:00"
            }
        }


class Message(MessageInDB):
    pass
