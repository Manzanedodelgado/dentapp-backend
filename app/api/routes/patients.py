from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.models.patient import Patient, PatientCreate, PatientUpdate
from app.database.mongodb import get_database

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=List[Patient])
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None
):
    """Listar pacientes con búsqueda opcional"""
    db = get_database()
    query = {}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = db.patients.find(query).skip(skip).limit(limit)
    patients = await cursor.to_list(length=limit)
    return patients


@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Obtener un paciente por ID"""
    db = get_database()
    
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
    
    patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return patient


@router.post("", response_model=Patient, status_code=201)
async def create_patient(patient: PatientCreate):
    """Crear un nuevo paciente"""
    db = get_database()
    
    patient_dict = patient.model_dump()
    patient_dict["created_at"] = datetime.utcnow()
    patient_dict["updated_at"] = datetime.utcnow()
    
    result = await db.patients.insert_one(patient_dict)
    created_patient = await db.patients.find_one({"_id": result.inserted_id})
    
    return created_patient


@router.put("/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient: PatientUpdate):
    """Actualizar un paciente"""
    db = get_database()
    
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
    
    update_data = {k: v for k, v in patient.model_dump(exclude_unset=True).items()}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.patients.update_one(
        {"_id": ObjectId(patient_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    updated_patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    return updated_patient


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(patient_id: str):
    """Eliminar un paciente"""
    db = get_database()
    
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
    
    result = await db.patients.delete_one({"_id": ObjectId(patient_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return None


@router.get("/{patient_id}/history")
async def get_patient_history(patient_id: str):
    """Obtener historial de citas de un paciente"""
    db = get_database()
    
    if not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=400, detail="ID de paciente inválido")
    
    # Verificar que el paciente existe
    patient = await db.patients.find_one({"_id": ObjectId(patient_id)})
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener citas del paciente
    cursor = db.appointments.find({"patient_id": patient_id}).sort("date", -1)
    appointments = await cursor.to_list(length=None)
    
    return {
        "patient": patient,
        "appointments": appointments
    }
