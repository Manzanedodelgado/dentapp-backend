from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from app.models.patient import PyObjectId


class ButtonAction(BaseModel):
    text: str
    action: str


class TemplateStep(BaseModel):
    content: str
    buttons: Optional[List[ButtonAction]] = []


class MessageTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    flow_steps: Optional[List[TemplateStep]] = []
    button_actions: Optional[List[ButtonAction]] = []


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    flow_steps: Optional[List[TemplateStep]] = None
    button_actions: Optional[List[ButtonAction]] = None


class MessageTemplateInDB(MessageTemplateBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MessageTemplate(MessageTemplateInDB):
    pass


class ConsentTemplateBase(BaseModel):
    treatment_type: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    digital_signature: bool = True


class ConsentTemplateCreate(ConsentTemplateBase):
    pass


class ConsentTemplateInDB(ConsentTemplateBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ConsentTemplate(ConsentTemplateInDB):
    pass
