from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class PatientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=9, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    whatsapp_registered: bool = False


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    phone: Optional[str] = Field(None, min_length=9, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    whatsapp_registered: Optional[bool] = None


class PatientInDB(PatientBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "María García López",
                "phone": "664123456",
                "email": "maria@example.com",
                "notes": "Paciente nuevo, primera visita gratis",
                "whatsapp_registered": True
            }
        }


class Patient(PatientInDB):
    pass
