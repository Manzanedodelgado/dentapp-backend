from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.models.conversation import Conversation, ConversationCreate, ConversationUpdate
from app.models.message import Message, MessageCreate
from app.database.mongodb import get_database

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=List[Conversation])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None
):
    """Listar conversaciones con filtro opcional por estado"""
    db = get_database()
    query = {}
    
    if status:
        query["status"] = status
    
    cursor = db.conversations.find(query).sort("last_message_at", -1).skip(skip).limit(limit)
    conversations = await cursor.to_list(length=limit)
    return conversations


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Obtener una conversación por ID"""
    db = get_database()
    
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=400, detail="ID de conversación inválido")
    
    conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    return conversation


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(conversation: ConversationCreate):
    """Crear una nueva conversación"""
    db = get_database()
    
    conversation_dict = conversation.model_dump()
    conversation_dict["created_at"] = datetime.utcnow()
    
    result = await db.conversations.insert_one(conversation_dict)
    created_conversation = await db.conversations.find_one({"_id": result.inserted_id})
    
    return created_conversation


@router.put("/{conversation_id}/status", response_model=Conversation)
async def update_conversation_status(conversation_id: str, status: str = Query(..., regex="^(yellow|blue|green|gray)$")):
    """Actualizar estado de clasificación de conversación"""
    db = get_database()
    
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=400, detail="ID de conversación inválido")
    
    result = await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"status": status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    updated_conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    return updated_conversation


@router.get("/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Obtener mensajes de una conversación"""
    db = get_database()
    
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=400, detail="ID de conversación inválido")
    
    # Verificar que la conversación existe
    conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    cursor = db.messages.find({"conversation_id": conversation_id}).sort("sent_at", 1).skip(skip).limit(limit)
    messages = await cursor.to_list(length=limit)
    return messages


@router.post("/{conversation_id}/messages", response_model=Message, status_code=201)
async def create_message(conversation_id: str, message: MessageCreate):
    """Crear un nuevo mensaje en una conversación"""
    db = get_database()
    
    if not ObjectId.is_valid(conversation_id):
        raise HTTPException(status_code=400, detail="ID de conversación inválido")
    
    # Verificar que la conversación existe
    conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    message_dict = message.model_dump()
    message_dict["conversation_id"] = conversation_id
    
    result = await db.messages.insert_one(message_dict)
    created_message = await db.messages.find_one({"_id": result.inserted_id})
    
    # Actualizar último mensaje de la conversación
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"last_message_at": datetime.utcnow()}}
    )
    
    return created_message
