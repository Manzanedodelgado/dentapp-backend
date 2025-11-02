from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.models.appointment import Appointment, AppointmentCreate, AppointmentUpdate
from app.database.mongodb import get_database

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=List[Appointment])
async def list_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    doctor: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    """Listar citas con filtros opcionales"""
    db = get_database()
    query = {}
    
    if doctor:
        query["doctor"] = doctor
    
    if status:
        query["status"] = status
    
    if date_from or date_to:
        query["date"] = {}
        if date_from:
            query["date"]["$gte"] = date_from
        if date_to:
            query["date"]["$lte"] = date_to
    
    cursor = db.appointments.find(query).sort("date", 1).skip(skip).limit(limit)
    appointments = await cursor.to_list(length=limit)
    return appointments


@router.get("/stats")
async def get_appointment_stats():
    """Obtener estadísticas de citas"""
    db = get_database()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total = await db.appointments.count_documents({})
    today_count = await db.appointments.count_documents({
        "date": {"$gte": today}
    })
    completed = await db.appointments.count_documents({"status": "completed"})
    scheduled = await db.appointments.count_documents({"status": "scheduled"})
    cancelled = await db.appointments.count_documents({"status": "cancelled"})
    
    return {
        "total": total,
        "today": today_count,
        "completed": completed,
        "scheduled": scheduled,
        "cancelled": cancelled
    }


@router.get("/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str):
    """Obtener una cita por ID"""
    db = get_database()
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="ID de cita inválido")
    
    appointment = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    return appointment


@router.post("", response_model=Appointment, status_code=201)
async def create_appointment(appointment: AppointmentCreate):
    """Crear una nueva cita"""
    db = get_database()
    
    # Verificar que el paciente existe
    if not ObjectId.is_valid(appointment.patient_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
    
    patient = await db.patients.find_one({"_id": ObjectId(appointment.patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    appointment_dict = appointment.model_dump()
    appointment_dict["created_at"] = datetime.utcnow()
    
    result = await db.appointments.insert_one(appointment_dict)
    created_appointment = await db.appointments.find_one({"_id": result.inserted_id})
    
    return created_appointment


@router.put("/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment: AppointmentUpdate):
    """Actualizar una cita"""
    db = get_database()
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="ID de cita inválido")
    
    update_data = {k: v for k, v in appointment.model_dump(exclude_unset=True).items()}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    result = await db.appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    updated_appointment = await db.appointments.find_one({"_id": ObjectId(appointment_id)})
    return updated_appointment


@router.delete("/{appointment_id}", status_code=204)
async def delete_appointment(appointment_id: str):
    """Eliminar una cita"""
    db = get_database()
    
    if not ObjectId.is_valid(appointment_id):
        raise HTTPException(status_code=400, detail="ID de cita inválido")
    
    result = await db.appointments.delete_one({"_id": ObjectId(appointment_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    return None
