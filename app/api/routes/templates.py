from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.models.template import MessageTemplate, MessageTemplateCreate, MessageTemplateUpdate
from app.models.template import ConsentTemplate, ConsentTemplateCreate
from app.database.mongodb import get_database

router = APIRouter(prefix="/templates", tags=["templates"])


# --- Message Templates ---

@router.get("/messages", response_model=List[MessageTemplate])
async def list_message_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Listar plantillas de mensajes"""
    db = get_database()
    cursor = db.message_templates.find({}).skip(skip).limit(limit)
    templates = await cursor.to_list(length=limit)
    return templates


@router.get("/messages/{template_id}", response_model=MessageTemplate)
async def get_message_template(template_id: str):
    """Obtener una plantilla por ID"""
    db = get_database()
    
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="ID de plantilla inválido")
    
    template = await db.message_templates.find_one({"_id": ObjectId(template_id)})
    
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return template


@router.post("/messages", response_model=MessageTemplate, status_code=201)
async def create_message_template(template: MessageTemplateCreate):
    """Crear una nueva plantilla de mensaje"""
    db = get_database()
    
    template_dict = template.model_dump()
    template_dict["created_at"] = datetime.utcnow()
    
    result = await db.message_templates.insert_one(template_dict)
    created_template = await db.message_templates.find_one({"_id": result.inserted_id})
    
    return created_template


@router.put("/messages/{template_id}", response_model=MessageTemplate)
async def update_message_template(template_id: str, template: MessageTemplateUpdate):
    """Actualizar una plantilla de mensaje"""
    db = get_database()
    
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="ID de plantilla inválido")
    
    update_data = {k: v for k, v in template.model_dump(exclude_unset=True).items()}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    result = await db.message_templates.update_one(
        {"_id": ObjectId(template_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    updated_template = await db.message_templates.find_one({"_id": ObjectId(template_id)})
    return updated_template


@router.delete("/messages/{template_id}", status_code=204)
async def delete_message_template(template_id: str):
    """Eliminar una plantilla de mensaje"""
    db = get_database()
    
    if not ObjectId.is_valid(template_id):
        raise HTTPException(status_code=400, detail="ID de plantilla inválido")
    
    result = await db.message_templates.delete_one({"_id": ObjectId(template_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return None


# --- Consent Templates ---

@router.get("/consents", response_model=List[ConsentTemplate])
async def list_consent_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Listar plantillas de consentimiento"""
    db = get_database()
    cursor = db.consent_templates.find({}).skip(skip).limit(limit)
    templates = await cursor.to_list(length=limit)
    return templates


@router.post("/consents", response_model=ConsentTemplate, status_code=201)
async def create_consent_template(template: ConsentTemplateCreate):
    """Crear una nueva plantilla de consentimiento"""
    db = get_database()
    
    template_dict = template.model_dump()
    template_dict["created_at"] = datetime.utcnow()
    
    result = await db.consent_templates.insert_one(template_dict)
    created_template = await db.consent_templates.find_one({"_id": result.inserted_id})
    
    return created_template
