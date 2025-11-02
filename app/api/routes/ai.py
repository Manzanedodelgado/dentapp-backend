from fastapi import APIRouter, HTTPException, Body
from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.models.ai_config import AIConfig, AIConfigCreate, AIConfigUpdate, AIResponse
from app.database.mongodb import get_database

router = APIRouter(prefix="/ai", tags=["ai"])


# Base de conocimientos predefinida
DENTAL_KNOWLEDGE_BASE = {
    "precios": {
        "primera_visita": {"precio": 0, "descripcion": "Primera visita GRATIS"},
        "limpieza_dental": {"precio": 45, "descripcion": "Limpieza dental completa"},
        "raspados": {"precio": 60, "descripcion": "Raspado por cuadrante"},
        "mantenimiento_periodontal": {"precio": 90, "descripcion": "Mantenimiento periodontal"},
        "estudio_periodontal": {"precio": 75, "descripcion": "Estudio periodontal completo"},
        "estudio_ortodoncia": {"precio": 100, "descripcion": "Estudio de ortodoncia fija"},
        "estudio_alineadores": {"precio": 1000, "descripcion": "Estudio para alineadores"},
        "brackets": {"precio": 700, "descripcion": "Colocación de brackets"},
        "mensualidad_ortodoncia": {"precio": 70, "descripcion": "Mensualidad ortodoncia fija"},
        "mensualidad_alineadores": {"precio": 125, "descripcion": "Mensualidad alineadores"},
        "implante": {"precio": 700, "descripcion": "Implante dental"},
        "endodoncia_uni": {"precio": 175, "descripcion": "Endodoncia uniradicular"},
        "endodoncia_multi": {"precio": 225, "descripcion": "Endodoncia multiradicular"},
        "corona_zirconio": {"precio": 400, "descripcion": "Corona de zirconio"},
        "blanqueamiento": {"precio": 250, "descripcion": "Blanqueamiento ambulatorio"},
        "blanqueamiento_clinica": {"precio": 300, "descripcion": "Blanqueamiento en clínica"},
        "botox": {"precio": 300, "descripcion": "Tratamiento con Botox"},
        "bichectomia": {"precio": 700, "descripcion": "Bichectomía"}
    },
    "horarios": {
        "lunes_jueves": "10:00-14:00 y 16:00-20:00",
        "viernes": "10:00-14:00"
    },
    "dentistas": {
        "mario": {
            "nombre": "Dr. Mario Rubio",
            "especialidad": "Implantología, Cirugía, Botox, Bichectomía",
            "dias": ["Lunes", "Miércoles", "Viernes"]
        },
        "rodriguez": {
            "nombre": "Dra. Rodriguez",
            "especialidad": "Endodoncia, Reconstrucciones, Prótesis",
            "dias": ["Martes", "Jueves"]
        },
        "gil": {
            "nombre": "Dra. Gil",
            "especialidad": "Endodoncia, Reconstrucciones, Prótesis",
            "dias": ["Martes", "Jueves", "Viernes"]
        }
    }
}


@router.get("/knowledge")
async def get_knowledge_base():
    """Obtener base de conocimientos del agente IA"""
    db = get_database()
    
    config = await db.ai_config.find_one({})
    
    if config:
        return config.get("knowledge_base", DENTAL_KNOWLEDGE_BASE)
    
    return DENTAL_KNOWLEDGE_BASE


@router.post("/classify")
async def classify_conversation(message: str = Body(..., embed=True)):
    """Clasificar conversación según contenido del mensaje"""
    
    message_lower = message.lower()
    
    # Palabras clave para clasificación
    urgente_keywords = ["urgente", "dolor", "emergencia", "duele", "sangra", "urgencia", "ahora"]
    normal_keywords = ["precio", "cita", "horario", "consulta", "cuando", "disponible"]
    
    # Clasificación
    if any(keyword in message_lower for keyword in urgente_keywords):
        classification = "yellow"
        confidence = 0.9
    elif any(keyword in message_lower for keyword in normal_keywords):
        classification = "blue"
        confidence = 0.8
    else:
        classification = "gray"
        confidence = 0.5
    
    return {
        "suggested_classification": classification,
        "confidence": confidence,
        "keywords_found": [kw for kw in (urgente_keywords + normal_keywords) if kw in message_lower]
    }


@router.post("/respond", response_model=AIResponse)
async def generate_ai_response(
    message: str = Body(..., description="Mensaje del paciente"),
    conversation_context: Optional[list] = Body(None, description="Contexto de mensajes anteriores")
):
    """Generar respuesta automática del agente IA"""
    
    message_lower = message.lower()
    knowledge = DENTAL_KNOWLEDGE_BASE
    
    # Determinar tipo de consulta
    if "precio" in message_lower or "cuesta" in message_lower or "coste" in message_lower:
        # Buscar tratamiento mencionado
        for tratamiento, info in knowledge["precios"].items():
            if tratamiento.replace("_", " ") in message_lower:
                response_text = f"El precio de {info['descripcion']} es {info['precio']}€. "
                if info['precio'] == 0:
                    response_text += "La primera visita es GRATIS. "
                response_text += "¿Te gustaría agendar una cita?"
                
                return AIResponse(
                    text=response_text,
                    confidence=0.95,
                    suggested_classification="blue",
                    requires_human=False
                )
        
        # Si no encuentra tratamiento específico
        return AIResponse(
            text="Tenemos varios tratamientos disponibles. ¿Sobre qué tratamiento específico te gustaría saber el precio? (limpieza, implante, ortodoncia, blanqueamiento, etc.)",
            confidence=0.7,
            suggested_classification="blue",
            requires_human=False
        )
    
    elif "horario" in message_lower or "cuando" in message_lower or "disponible" in message_lower:
        response_text = f"Nuestros horarios son:\n"
        response_text += f"Lunes a Jueves: {knowledge['horarios']['lunes_jueves']}\n"
        response_text += f"Viernes: {knowledge['horarios']['viernes']}\n"
        response_text += "¿Qué día te viene mejor?"
        
        return AIResponse(
            text=response_text,
            confidence=0.9,
            suggested_classification="blue",
            requires_human=False
        )
    
    elif "cita" in message_lower or "agendar" in message_lower or "reservar" in message_lower:
        response_text = "Para agendar una cita necesito saber:\n"
        response_text += "1. ¿Qué tratamiento necesitas?\n"
        response_text += "2. ¿Qué día te viene mejor?\n"
        response_text += "3. ¿Prefieres mañana o tarde?"
        
        return AIResponse(
            text=response_text,
            confidence=0.85,
            suggested_classification="blue",
            requires_human=False
        )
    
    elif any(word in message_lower for word in ["dolor", "duele", "urgente", "emergencia"]):
        return AIResponse(
            text="Entiendo que es urgente. Te recomiendo llamar directamente a nuestra clínica al 664 218 253 para atenderte lo antes posible.",
            confidence=0.95,
            suggested_classification="yellow",
            requires_human=True
        )
    
    else:
        # Respuesta genérica
        return AIResponse(
            text="Gracias por contactar con Rubio Garcia Dental. ¿En qué puedo ayudarte? Puedo informarte sobre precios, horarios o ayudarte a agendar una cita.",
            confidence=0.6,
            suggested_classification="gray",
            requires_human=False
        )


@router.get("/config", response_model=AIConfig)
async def get_ai_config():
    """Obtener configuración del agente IA"""
    db = get_database()
    
    config = await db.ai_config.find_one({})
    
    if not config:
        # Crear configuración por defecto
        default_config = {
            "knowledge_base": DENTAL_KNOWLEDGE_BASE,
            "auto_responses": True,
            "classification_rules": [
                {"keywords": ["urgente", "dolor"], "action": "yellow"},
                {"keywords": ["precio", "cita"], "action": "blue"}
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.ai_config.insert_one(default_config)
        config = await db.ai_config.find_one({"_id": result.inserted_id})
    
    return config


@router.put("/config", response_model=AIConfig)
async def update_ai_config(config: AIConfigUpdate):
    """Actualizar configuración del agente IA"""
    db = get_database()
    
    update_data = {k: v for k, v in config.model_dump(exclude_unset=True).items()}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    update_data["updated_at"] = datetime.utcnow()
    
    existing_config = await db.ai_config.find_one({})
    
    if existing_config:
        await db.ai_config.update_one(
            {"_id": existing_config["_id"]},
            {"$set": update_data}
        )
        updated_config = await db.ai_config.find_one({"_id": existing_config["_id"]})
    else:
        update_data["created_at"] = datetime.utcnow()
        result = await db.ai_config.insert_one(update_data)
        updated_config = await db.ai_config.find_one({"_id": result.inserted_id})
    
    return updated_config
