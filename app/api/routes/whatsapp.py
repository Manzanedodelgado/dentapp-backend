from fastapi import APIRouter, HTTPException, Body
import httpx
from app.core.config import settings
from app.database.mongodb import get_database
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/status")
async def get_whatsapp_status():
    """Obtener estado de conexión de WhatsApp"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WHATSAPP_SERVICE_URL}/status",
                timeout=5.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Servicio WhatsApp no disponible: {str(e)}"
        )


@router.get("/qr")
async def get_qr_code():
    """Obtener código QR para vincular WhatsApp"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WHATSAPP_SERVICE_URL}/qr",
                timeout=5.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo obtener QR: {str(e)}"
        )


@router.post("/send-message")
async def send_whatsapp_message(
    to: str = Body(..., description="Número de teléfono destino"),
    message: str = Body(..., description="Mensaje a enviar"),
    conversation_id: str = Body(None, description="ID de conversación (opcional)")
):
    """Enviar mensaje de WhatsApp"""
    db = get_database()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.WHATSAPP_SERVICE_URL}/send-message",
                json={"to": to, "message": message},
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error al enviar mensaje"
                )
            
            # Guardar mensaje en base de datos si existe conversación
            if conversation_id and ObjectId.is_valid(conversation_id):
                message_doc = {
                    "conversation_id": conversation_id,
                    "type": "text",
                    "content": message,
                    "sender": "clinic",
                    "sent_at": datetime.utcnow()
                }
                await db.messages.insert_one(message_doc)
                
                # Actualizar último mensaje
                await db.conversations.update_one(
                    {"_id": ObjectId(conversation_id)},
                    {"$set": {"last_message_at": datetime.utcnow()}}
                )
            
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error al conectar con servicio WhatsApp: {str(e)}"
        )


@router.post("/webhook")
async def whatsapp_webhook(payload: dict):
    """Recibir mensajes entrantes de WhatsApp"""
    db = get_database()
    
    try:
        # Extraer datos del mensaje
        phone = payload.get("from")
        message = payload.get("message")
        
        if not phone or not message:
            raise HTTPException(status_code=400, detail="Datos incompletos")
        
        # Buscar o crear conversación
        conversation = await db.conversations.find_one({"whatsapp_number": phone})
        
        if not conversation:
            # Crear nueva conversación
            conversation_doc = {
                "whatsapp_number": phone,
                "status": "gray",
                "last_message_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            }
            result = await db.conversations.insert_one(conversation_doc)
            conversation_id = str(result.inserted_id)
        else:
            conversation_id = str(conversation["_id"])
        
        # Guardar mensaje
        message_doc = {
            "conversation_id": conversation_id,
            "type": "text",
            "content": message,
            "sender": "patient",
            "sent_at": datetime.utcnow()
        }
        await db.messages.insert_one(message_doc)
        
        # Actualizar última actividad
        await db.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"last_message_at": datetime.utcnow()}}
        )
        
        return {"success": True, "conversation_id": conversation_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
