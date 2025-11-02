"""
Rutas API para Sistema de Comunicación Automatizada
Rubio Garcia Dentapp - Email, SMS, WhatsApp
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from ...database import db
from ...models.communication import (
    CommunicationTemplate,
    CommunicationTemplateInDB,
    CommunicationCampaign,
    CommunicationCampaignInDB,
    PatientCommunicationPreferences,
    PatientCommunicationPreferencesInDB,
    CommunicationConfig,
    CommunicationConfigInDB,
    SMTPConfig,
    TwilioConfig
)
from ...services.email_service import EmailService
from ...services.sms_service import SMSService
from ...services.automation_service import AutomationService

router = APIRouter(prefix="/communication", tags=["Communication"])

# Instancias globales de servicios (se inicializarán en startup)
email_service: Optional[EmailService] = None
sms_service: Optional[SMSService] = None
automation_service: Optional[AutomationService] = None


# ==================== TEMPLATES ====================

@router.get("/templates")
async def list_templates(
    type: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Listar templates de comunicación
    
    Query params:
    - type: Filtrar por tipo (email, sms, whatsapp)
    - category: Filtrar por categoría
    - is_active: Filtrar por estado activo
    """
    try:
        query = {}
        
        if type:
            query["type"] = type
        if category:
            query["category"] = category
        if is_active is not None:
            query["is_active"] = is_active
        
        templates = await db.communication_templates.find(query).skip(skip).limit(limit).to_list(length=limit)
        
        return {
            "templates": templates,
            "count": len(templates),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando templates: {str(e)}")


@router.post("/templates")
async def create_template(template: CommunicationTemplate):
    """Crear nuevo template de comunicación"""
    try:
        template_dict = template.dict()
        template_dict["created_at"] = datetime.utcnow()
        template_dict["updated_at"] = datetime.utcnow()
        
        result = await db.communication_templates.insert_one(template_dict)
        
        created_template = await db.communication_templates.find_one({"_id": result.inserted_id})
        
        return {
            "success": True,
            "template": created_template,
            "message": "Template creado exitosamente"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando template: {str(e)}")


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Obtener template específico"""
    try:
        if not ObjectId.is_valid(template_id):
            raise HTTPException(status_code=400, detail="ID de template inválido")
        
        template = await db.communication_templates.find_one({"_id": ObjectId(template_id)})
        
        if not template:
            raise HTTPException(status_code=404, detail="Template no encontrado")
        
        return template
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo template: {str(e)}")


@router.put("/templates/{template_id}")
async def update_template(template_id: str, template: CommunicationTemplate):
    """Actualizar template existente"""
    try:
        if not ObjectId.is_valid(template_id):
            raise HTTPException(status_code=400, detail="ID de template inválido")
        
        existing = await db.communication_templates.find_one({"_id": ObjectId(template_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Template no encontrado")
        
        template_dict = template.dict()
        template_dict["updated_at"] = datetime.utcnow()
        
        # Preservar created_at
        template_dict["created_at"] = existing["created_at"]
        
        await db.communication_templates.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": template_dict}
        )
        
        updated_template = await db.communication_templates.find_one({"_id": ObjectId(template_id)})
        
        return {
            "success": True,
            "template": updated_template,
            "message": "Template actualizado exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando template: {str(e)}")


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str):
    """Eliminar template"""
    try:
        if not ObjectId.is_valid(template_id):
            raise HTTPException(status_code=400, detail="ID de template inválido")
        
        result = await db.communication_templates.delete_one({"_id": ObjectId(template_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template no encontrado")
        
        return {
            "success": True,
            "message": "Template eliminado exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando template: {str(e)}")


@router.post("/templates/{template_id}/preview")
async def preview_template(template_id: str, template_data: dict):
    """Previsualizar template con datos de prueba"""
    try:
        if not ObjectId.is_valid(template_id):
            raise HTTPException(status_code=400, detail="ID de template inválido")
        
        template = await db.communication_templates.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise HTTPException(status_code=404, detail="Template no encontrado")
        
        # Procesar template con datos de prueba
        if email_service:
            processed_html = email_service.process_template(template["html_content"], template_data)
            processed_text = email_service.process_template(template.get("text_content", ""), template_data)
        else:
            # Fallback si no hay servicio de email
            import re
            processed_html = template["html_content"]
            processed_text = template.get("text_content", "")
            for key, value in template_data.items():
                pattern = r'\{\{\s*' + key + r'\s*\}\}'
                processed_html = re.sub(pattern, str(value), processed_html)
                processed_text = re.sub(pattern, str(value), processed_text)
        
        return {
            "template_id": template_id,
            "template_name": template["name"],
            "type": template["type"],
            "subject": template.get("subject", ""),
            "html_content": processed_html,
            "text_content": processed_text,
            "template_data": template_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previsualizando template: {str(e)}")


# ==================== CAMPAÑAS ====================

@router.get("/campaigns")
async def list_campaigns(
    status: Optional[str] = None,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Listar campañas de comunicación"""
    try:
        query = {}
        
        if status:
            query["status"] = status
        if type:
            query["type"] = type
        
        campaigns = await db.communication_campaigns.find(query).skip(skip).limit(limit).to_list(length=limit)
        
        return {
            "campaigns": campaigns,
            "count": len(campaigns),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listando campañas: {str(e)}")


@router.post("/campaigns")
async def create_campaign(campaign: CommunicationCampaign):
    """Crear nueva campaña"""
    try:
        campaign_dict = campaign.dict()
        campaign_dict["created_at"] = datetime.utcnow()
        campaign_dict["updated_at"] = datetime.utcnow()
        campaign_dict["status"] = "draft"
        
        result = await db.communication_campaigns.insert_one(campaign_dict)
        
        created_campaign = await db.communication_campaigns.find_one({"_id": result.inserted_id})
        
        return {
            "success": True,
            "campaign": created_campaign,
            "message": "Campaña creada exitosamente"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando campaña: {str(e)}")


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Obtener campaña específica"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="ID de campaña inválido")
        
        campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
        return campaign
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo campaña: {str(e)}")


@router.put("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, campaign: CommunicationCampaign):
    """Actualizar campaña"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="ID de campaña inválido")
        
        existing = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
        campaign_dict = campaign.dict()
        campaign_dict["updated_at"] = datetime.utcnow()
        campaign_dict["created_at"] = existing["created_at"]
        
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": campaign_dict}
        )
        
        updated_campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        
        return {
            "success": True,
            "campaign": updated_campaign,
            "message": "Campaña actualizada exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando campaña: {str(e)}")


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """Eliminar campaña"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="ID de campaña inválido")
        
        campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
        if campaign["status"] in ["sending", "completed"]:
            raise HTTPException(status_code=400, detail="No se puede eliminar campaña en ejecución o completada")
        
        result = await db.communication_campaigns.delete_one({"_id": ObjectId(campaign_id)})
        
        return {
            "success": True,
            "message": "Campaña eliminada exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando campaña: {str(e)}")


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, background_tasks: BackgroundTasks):
    """Enviar campaña (procesar en background)"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="ID de campaña inválido")
        
        campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
        if campaign["status"] != "draft":
            raise HTTPException(status_code=400, detail="Solo se pueden enviar campañas en borrador")
        
        # Actualizar estado a scheduled
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "scheduled",
                "scheduled_at": datetime.utcnow()
            }}
        )
        
        # Añadir tarea en background para procesamiento
        background_tasks.add_task(process_campaign, campaign_id)
        
        return {
            "success": True,
            "message": "Campaña programada para envío",
            "campaign_id": campaign_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando campaña: {str(e)}")


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: str):
    """Cancelar campaña programada"""
    try:
        if not ObjectId.is_valid(campaign_id):
            raise HTTPException(status_code=400, detail="ID de campaña inválido")
        
        campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaña no encontrada")
        
        if campaign["status"] not in ["scheduled", "sending"]:
            raise HTTPException(status_code=400, detail="Solo se pueden cancelar campañas programadas o en envío")
        
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"status": "cancelled"}}
        )
        
        return {
            "success": True,
            "message": "Campaña cancelada exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelando campaña: {str(e)}")


# ==================== PREFERENCIAS DE PACIENTES ====================

@router.get("/preferences/{patient_id}")
async def get_patient_preferences(patient_id: str):
    """Obtener preferencias de comunicación de un paciente"""
    try:
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
        # Verificar que el paciente existe
        patient = await db.pacientes.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        preferences = await db.patient_communication_preferences.find_one({"patient_id": patient_id})
        
        if not preferences:
            # Retornar preferencias por defecto
            return {
                "patient_id": patient_id,
                "preferred_channels": {
                    "email": True,
                    "sms": True,
                    "whatsapp": True,
                    "phone_call": False
                },
                "preferred_times": {
                    "morning_start": "09:00",
                    "morning_end": "12:00",
                    "afternoon_start": "16:00",
                    "afternoon_end": "20:00",
                    "timezone": "Europe/Madrid"
                },
                "communication_types": {
                    "appointment_reminders": True,
                    "treatment_reminders": True,
                    "promotional_offers": False,
                    "health_tips": True,
                    "survey_requests": True
                },
                "frequency_limits": {
                    "max_sms_per_week": 3,
                    "max_emails_per_week": 5,
                    "quiet_hours": {
                        "start": "22:00",
                        "end": "08:00"
                    }
                },
                "language_preference": "es",
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": "default"
            }
        
        return preferences
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo preferencias: {str(e)}")


@router.put("/preferences/{patient_id}")
async def update_patient_preferences(patient_id: str, preferences: PatientCommunicationPreferences):
    """Actualizar preferencias de comunicación de un paciente"""
    try:
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
        # Verificar que el paciente existe
        patient = await db.pacientes.find_one({"_id": ObjectId(patient_id)})
        if not patient:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        preferences_dict = preferences.dict()
        preferences_dict["patient_id"] = patient_id
        preferences_dict["updated_at"] = datetime.utcnow()
        
        # Upsert
        await db.patient_communication_preferences.update_one(
            {"patient_id": patient_id},
            {"$set": preferences_dict},
            upsert=True
        )
        
        updated_preferences = await db.patient_communication_preferences.find_one({"patient_id": patient_id})
        
        return {
            "success": True,
            "preferences": updated_preferences,
            "message": "Preferencias actualizadas exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando preferencias: {str(e)}")


@router.post("/preferences/bulk-update")
async def bulk_update_preferences(updates: List[dict]):
    """Actualización masiva de preferencias"""
    try:
        updated_count = 0
        
        for update in updates:
            patient_id = update.get("patient_id")
            preferences_data = update.get("preferences")
            
            if not patient_id or not preferences_data:
                continue
            
            preferences_data["patient_id"] = patient_id
            preferences_data["updated_at"] = datetime.utcnow()
            
            await db.patient_communication_preferences.update_one(
                {"patient_id": patient_id},
                {"$set": preferences_data},
                upsert=True
            )
            
            updated_count += 1
        
        return {
            "success": True,
            "updated_count": updated_count,
            "total": len(updates)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en actualización masiva: {str(e)}")


# ==================== FUNCIONES AUXILIARES ====================

async def process_campaign(campaign_id: str):
    """Procesar envío de campaña (función background)"""
    try:
        campaign = await db.communication_campaigns.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            return
        
        # Actualizar estado
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"status": "sending"}}
        )
        
        # Obtener destinatarios según criterios
        # (implementación simplificada)
        
        # Al finalizar
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }}
        )
    
    except Exception as e:
        # Actualizar estado a error
        await db.communication_campaigns.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"status": "cancelled", "error": str(e)}}
        )


# ==================== ANALYTICS ====================

@router.get("/analytics/overview")
async def get_analytics_overview(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """Obtener resumen general de analytics de comunicación"""
    try:
        # Parsear fechas
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        # Métricas globales
        total_sent = await db.communication_logs.count_documents({
            "sent_at": {"$gte": inicio, "$lte": fin}
        })
        
        total_delivered = await db.communication_logs.count_documents({
            "sent_at": {"$gte": inicio, "$lte": fin},
            "status": "delivered"
        })
        
        total_opened = await db.communication_logs.count_documents({
            "sent_at": {"$gte": inicio, "$lte": fin},
            "opened_at": {"$exists": True}
        })
        
        total_clicked = await db.communication_logs.count_documents({
            "sent_at": {"$gte": inicio, "$lte": fin},
            "clicked_at": {"$exists": True}
        })
        
        total_replied = await db.communication_logs.count_documents({
            "sent_at": {"$gte": inicio, "$lte": fin},
            "replied_at": {"$exists": True}
        })
        
        return {
            "periodo": {
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat()
            },
            "global_metrics": {
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_opened": total_opened,
                "total_clicked": total_clicked,
                "total_replied": total_replied,
                "delivery_rate": round((total_delivered / total_sent * 100) if total_sent > 0 else 0, 2),
                "open_rate": round((total_opened / total_delivered * 100) if total_delivered > 0 else 0, 2),
                "click_rate": round((total_clicked / total_opened * 100) if total_opened > 0 else 0, 2),
                "response_rate": round((total_replied / total_sent * 100) if total_sent > 0 else 0, 2)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo overview: {str(e)}")


@router.get("/analytics/channels")
async def get_channel_analytics(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """Obtener analytics por canal"""
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        # Analytics por canal
        pipeline = [
            {"$match": {"sent_at": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": "$channel_type",
                "sent": {"$sum": 1},
                "delivered": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                "opened": {"$sum": {"$cond": [{"$ne": ["$opened_at", None]}, 1, 0]}},
                "clicked": {"$sum": {"$cond": [{"$ne": ["$clicked_at", None]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}}
            }}
        ]
        
        channel_data = await db.communication_logs.aggregate(pipeline).to_list(length=None)
        
        # Formatear resultados
        channels = {}
        for data in channel_data:
            channel_type = data["_id"]
            channels[channel_type] = {
                "sent": data["sent"],
                "delivered": data["delivered"],
                "opened": data.get("opened", 0),
                "clicked": data.get("clicked", 0),
                "failed": data["failed"],
                "delivery_rate": round((data["delivered"] / data["sent"] * 100) if data["sent"] > 0 else 0, 2),
                "open_rate": round((data.get("opened", 0) / data["delivered"] * 100) if data["delivered"] > 0 else 0, 2)
            }
        
        return {
            "periodo": {
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat()
            },
            "channel_metrics": channels
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo analytics de canales: {str(e)}")


@router.get("/analytics/templates")
async def get_template_performance(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    limit: int = 20
):
    """Obtener performance de templates"""
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        pipeline = [
            {"$match": {"sent_at": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": "$template_id",
                "sent": {"$sum": 1},
                "delivered": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                "opened": {"$sum": {"$cond": [{"$ne": ["$opened_at", None]}, 1, 0]}},
                "clicked": {"$sum": {"$cond": [{"$ne": ["$clicked_at", None]}, 1, 0]}},
                "replied": {"$sum": {"$cond": [{"$ne": ["$replied_at", None]}, 1, 0]}}
            }},
            {"$sort": {"sent": -1}},
            {"$limit": limit}
        ]
        
        template_data = await db.communication_logs.aggregate(pipeline).to_list(length=limit)
        
        # Enriquecer con información de templates
        performance = []
        for data in template_data:
            template_id = data["_id"]
            
            # Obtener template info
            if template_id and ObjectId.is_valid(template_id):
                template = await db.communication_templates.find_one({"_id": ObjectId(template_id)})
                template_name = template["name"] if template else "Unknown"
                template_type = template["type"] if template else "unknown"
            else:
                template_name = "Sin template"
                template_type = "unknown"
            
            delivered = data["delivered"]
            opened = data["opened"]
            
            performance.append({
                "template_id": template_id,
                "template_name": template_name,
                "type": template_type,
                "sent": data["sent"],
                "open_rate": round((opened / delivered * 100) if delivered > 0 else 0, 2),
                "click_rate": round((data["clicked"] / opened * 100) if opened > 0 else 0, 2),
                "response_rate": round((data["replied"] / data["sent"] * 100) if data["sent"] > 0 else 0, 2)
            })
        
        return {"template_performance": performance}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo performance de templates: {str(e)}")


@router.get("/analytics/trends")
async def get_communication_trends(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """Obtener tendencias temporales"""
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        pipeline = [
            {"$match": {"sent_at": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$sent_at"},
                    "month": {"$month": "$sent_at"},
                    "day": {"$dayOfMonth": "$sent_at"}
                },
                "sent": {"$sum": 1},
                "delivered": {"$sum": {"$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]}},
                "opened": {"$sum": {"$cond": [{"$ne": ["$opened_at", None]}, 1, 0]}}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
        ]
        
        trend_data = await db.communication_logs.aggregate(pipeline).to_list(length=None)
        
        trends = [
            {
                "date": f"{t['_id']['year']}-{t['_id']['month']:02d}-{t['_id']['day']:02d}",
                "sent": t["sent"],
                "delivered": t["delivered"],
                "opened": t["opened"]
            }
            for t in trend_data
        ]
        
        return {"trends": trends}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo tendencias: {str(e)}")


@router.get("/analytics/performance")
async def get_overall_performance():
    """Obtener performance general del sistema"""
    try:
        # Estadísticas globales
        total_templates = await db.communication_templates.count_documents({})
        active_templates = await db.communication_templates.count_documents({"is_active": True})
        
        total_campaigns = await db.communication_campaigns.count_documents({})
        completed_campaigns = await db.communication_campaigns.count_documents({"status": "completed"})
        
        total_patients_with_prefs = await db.patient_communication_preferences.count_documents({})
        
        # Últimos 7 días
        last_week = datetime.now() - timedelta(days=7)
        messages_last_week = await db.communication_logs.count_documents({
            "sent_at": {"$gte": last_week}
        })
        
        return {
            "summary": {
                "total_templates": total_templates,
                "active_templates": active_templates,
                "total_campaigns": total_campaigns,
                "completed_campaigns": completed_campaigns,
                "patients_with_preferences": total_patients_with_prefs,
                "messages_last_7_days": messages_last_week
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo performance: {str(e)}")


# ==================== CONFIGURACIÓN ====================

@router.get("/config/smtp")
async def get_smtp_config():
    """Obtener configuración SMTP (sin contraseña)"""
    try:
        config = await db.communication_config.find_one({})
        
        if not config or not config.get("smtp"):
            return {"configured": False}
        
        smtp = config["smtp"]
        
        # No enviar contraseña
        return {
            "configured": True,
            "server": smtp.get("server"),
            "port": smtp.get("port"),
            "username": smtp.get("username"),
            "use_tls": smtp.get("use_tls", True),
            "from_name": smtp.get("from_name"),
            "from_email": smtp.get("from_email")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo config SMTP: {str(e)}")


@router.put("/config/smtp")
async def update_smtp_config(smtp_config: SMTPConfig):
    """Actualizar configuración SMTP"""
    try:
        # Obtener o crear configuración
        config = await db.communication_config.find_one({})
        
        smtp_dict = smtp_config.dict()
        
        if config:
            await db.communication_config.update_one(
                {"_id": config["_id"]},
                {"$set": {
                    "smtp": smtp_dict,
                    "updated_at": datetime.utcnow()
                }}
            )
        else:
            await db.communication_config.insert_one({
                "smtp": smtp_dict,
                "updated_at": datetime.utcnow(),
                "updated_by": "admin"
            })
        
        # Reinicializar servicio de email global
        global email_service
        email_service = EmailService(smtp_dict)
        
        return {
            "success": True,
            "message": "Configuración SMTP actualizada exitosamente"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando config SMTP: {str(e)}")


@router.get("/config/sms")
async def get_sms_config():
    """Obtener configuración SMS (sin auth token)"""
    try:
        config = await db.communication_config.find_one({})
        
        if not config or not config.get("twilio"):
            return {"configured": False}
        
        twilio = config["twilio"]
        
        return {
            "configured": True,
            "account_sid": twilio.get("account_sid"),
            "from_number": twilio.get("from_number")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo config SMS: {str(e)}")


@router.put("/config/sms")
async def update_sms_config(twilio_config: TwilioConfig):
    """Actualizar configuración SMS (Twilio)"""
    try:
        config = await db.communication_config.find_one({})
        
        twilio_dict = twilio_config.dict()
        
        if config:
            await db.communication_config.update_one(
                {"_id": config["_id"]},
                {"$set": {
                    "twilio": twilio_dict,
                    "updated_at": datetime.utcnow()
                }}
            )
        else:
            await db.communication_config.insert_one({
                "twilio": twilio_dict,
                "updated_at": datetime.utcnow(),
                "updated_by": "admin"
            })
        
        # Reinicializar servicio SMS global
        global sms_service
        sms_service = SMSService(twilio_dict)
        
        return {
            "success": True,
            "message": "Configuración SMS actualizada exitosamente"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando config SMS: {str(e)}")


@router.get("/config/whatsapp")
async def get_whatsapp_config():
    """Obtener configuración WhatsApp"""
    try:
        config = await db.communication_config.find_one({})
        
        if not config or not config.get("whatsapp"):
            return {
                "configured": True,  # Usar configuración por defecto
                "service_url": "http://localhost:3001"
            }
        
        return {
            "configured": True,
            "service_url": config["whatsapp"].get("service_url", "http://localhost:3001")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo config WhatsApp: {str(e)}")


@router.post("/config/test-email")
async def test_email_connection(test_to: str = Query(..., description="Email de prueba")):
    """Probar conexión SMTP enviando email de prueba"""
    try:
        if not email_service:
            raise HTTPException(status_code=400, detail="Servicio de email no configurado")
        
        # Test de conexión
        connection_test = email_service.test_connection()
        
        if not connection_test.get("success"):
            return connection_test
        
        # Enviar email de prueba
        result = email_service.send_email(
            to=[test_to],
            subject="Test - Rubio García Sistema de Comunicación",
            html_content="<h1>Test exitoso</h1><p>Este es un email de prueba del sistema de comunicación automatizada.</p>",
            text_content="Test exitoso\n\nEste es un email de prueba del sistema de comunicación automatizada.",
            template_data={}
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error probando email: {str(e)}")


@router.post("/config/test-sms")
async def test_sms_connection(test_to: str = Query(..., description="Teléfono de prueba (+34XXXXXXXXX)")):
    """Probar conexión SMS enviando mensaje de prueba"""
    try:
        if not sms_service:
            raise HTTPException(status_code=400, detail="Servicio de SMS no configurado")
        
        # Test de conexión
        connection_test = sms_service.test_connection()
        
        if not connection_test.get("success") and not connection_test.get("dev_mode"):
            return connection_test
        
        # Enviar SMS de prueba
        result = sms_service.send_sms(
            to=[test_to],
            message="Test Rubio García: Sistema de comunicación configurado correctamente.",
            template_data={}
        )
        
        return {"success": True, "results": result}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error probando SMS: {str(e)}")


@router.get("/config/automation-status")
async def get_automation_status():
    """Obtener estado del sistema de automatización"""
    try:
        config = await db.communication_config.find_one({})
        
        if not config:
            return {
                "automation_enabled": False,
                "auto_reminders": False,
                "no_show_followup": False,
                "scheduler_running": False
            }
        
        return {
            "automation_enabled": config.get("enable_auto_reminders", True),
            "auto_reminders": config.get("enable_auto_reminders", True),
            "no_show_followup": config.get("enable_no_show_followup", True),
            "scheduler_running": automation_service.is_running if automation_service else False,
            "daily_limits": {
                "email": config.get("daily_email_limit", 1000),
                "sms": config.get("daily_sms_limit", 500)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")


@router.post("/config/toggle-automation")
async def toggle_automation(enable: bool = Query(...)):
    """Activar/desactivar sistema de automatización"""
    try:
        config = await db.communication_config.find_one({})
        
        if config:
            await db.communication_config.update_one(
                {"_id": config["_id"]},
                {"$set": {
                    "enable_auto_reminders": enable,
                    "updated_at": datetime.utcnow()
                }}
            )
        else:
            await db.communication_config.insert_one({
                "enable_auto_reminders": enable,
                "updated_at": datetime.utcnow()
            })
        
        # Controlar scheduler
        if automation_service:
            if enable:
                automation_service.start()
            else:
                automation_service.stop()
        
        return {
            "success": True,
            "enabled": enable,
            "message": f"Automatización {'activada' if enable else 'desactivada'} exitosamente"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling automation: {str(e)}")
