from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.patient import PyObjectId


class AppointmentBase(BaseModel):
    patient_id: str = Field(..., description="ID del paciente")
    title: str = Field(..., min_length=1, max_length=200)
    date: datetime = Field(..., description="Fecha y hora de la cita")
    hora: str = Field(..., description="Hora de la cita (formato HH:MM) - Campo crítico para Google Sheets")
    duration_minutes: int = Field(default=30, ge=15, le=240)
    status: str = Field(default="scheduled", description="scheduled, completed, cancelled")
    doctor: str = Field(..., description="mario, rodriguez, gil")
    treatment_type: Optional[str] = Field(None, max_length=200)
    reminder_enabled: bool = True


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    patient_id: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    date: Optional[datetime] = None
    hora: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=240)
    status: Optional[str] = None
    doctor: Optional[str] = None
    treatment_type: Optional[str] = None
    reminder_enabled: Optional[bool] = None


class AppointmentInDB(AppointmentBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "patient_id": "507f1f77bcf86cd799439011",
                "title": "Limpieza dental",
                "date": "2025-11-01T10:00:00",
                "hora": "10:00",
                "duration_minutes": 30,
                "status": "scheduled",
                "doctor": "mario",
                "treatment_type": "Limpieza",
                "reminder_enabled": True
            }
        }


class Appointment(AppointmentInDB):
    pass
