"""
Servicio de Automatización para Recordatorios
Rubio Garcia Dentapp - APScheduler
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from ..database import db
from .email_service import EmailService
from .sms_service import SMSService

logger = logging.getLogger(__name__)


class AutomationService:
    """Servicio de automatización de recordatorios y seguimientos"""
    
    def __init__(self, email_service: EmailService, sms_service: SMSService):
        """
        Inicializar servicio de automatización
        
        Args:
            email_service: Servicio de email
            sms_service: Servicio de SMS
        """
        self.email_service = email_service
        self.sms_service = sms_service
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        logger.info("AutomationService initialized")
    
    def start(self):
        """Iniciar scheduler de automatización"""
        if not self.is_running:
            self.schedule_reminder_jobs()
            self.scheduler.start()
            self.is_running = True
            logger.info("Automation scheduler started")
    
    def stop(self):
        """Detener scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Automation scheduler stopped")
    
    def schedule_reminder_jobs(self):
        """Programar trabajos de recordatorios automáticos"""
        
        # Recordatorio 24 horas antes - ejecutar a las 9 AM todos los días
        self.scheduler.add_job(
            self.send_24h_reminders,
            CronTrigger(hour=9, minute=0),
            id='reminder_24h',
            name='Recordatorio 24 horas',
            replace_existing=True
        )
        
        # Recordatorio 2 horas antes - ejecutar cada hora
        self.scheduler.add_job(
            self.send_2h_reminders,
            CronTrigger(minute=0),  # Cada hora en punto
            id='reminder_2h',
            name='Recordatorio 2 horas',
            replace_existing=True
        )
        
        # Seguimiento de no-shows - ejecutar a las 10 AM todos los días
        self.scheduler.add_job(
            self.followup_no_shows,
            CronTrigger(hour=10, minute=0),
            id='no_show_followup',
            name='Seguimiento No-Shows',
            replace_existing=True
        )
        
        # Post-visit follow-up - ejecutar a las 11 AM todos los días
        self.scheduler.add_job(
            self.send_post_visit_messages,
            CronTrigger(hour=11, minute=0),
            id='post_visit',
            name='Seguimiento Post-Visita',
            replace_existing=True
        )
        
        logger.info("Reminder jobs scheduled")
    
    async def send_24h_reminders(self):
        """Enviar recordatorios 24 horas antes de la cita"""
        try:
            logger.info("Ejecutando recordatorios 24h...")
            
            # Obtener citas de mañana
            tomorrow_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            tomorrow_end = tomorrow_start + timedelta(days=1)
            
            appointments = await db.citas.find({
                "fecha": {
                    "$gte": tomorrow_start,
                    "$lt": tomorrow_end
                },
                "estado": {"$in": ["programada", "confirmada"]}
            }).to_list(length=None)
            
            logger.info(f"Encontradas {len(appointments)} citas para mañana")
            
            sent_count = 0
            for appointment in appointments:
                # Obtener datos del paciente
                patient = await db.pacientes.find_one({"_id": appointment["paciente_id"]})
                if not patient:
                    continue
                
                # Verificar preferencias
                preferences = await self.get_patient_preferences(str(appointment["paciente_id"]))
                
                if not preferences.get("communication_types", {}).get("appointment_reminders", True):
                    logger.info(f"Paciente {patient.get('nombre')} no desea recordatorios")
                    continue
                
                # Obtener template
                template = await self.get_template("reminder_24h", "email")
                if not template:
                    logger.warning("Template reminder_24h no encontrado")
                    continue
                
                # Preparar datos
                template_data = await self.prepare_appointment_data(appointment, patient)
                
                # Enviar según preferencias
                await self.send_based_on_preferences(
                    patient,
                    template,
                    template_data,
                    preferences
                )
                
                sent_count += 1
            
            logger.info(f"Recordatorios 24h enviados: {sent_count}")
        
        except Exception as e:
            logger.error(f"Error en recordatorios 24h: {str(e)}")
    
    async def send_2h_reminders(self):
        """Enviar recordatorios 2 horas antes de la cita"""
        try:
            logger.info("Ejecutando recordatorios 2h...")
            
            # Obtener citas en las próximas 2-3 horas
            now = datetime.now()
            window_start = now + timedelta(hours=2)
            window_end = now + timedelta(hours=3)
            
            appointments = await db.citas.find({
                "fecha": {
                    "$gte": window_start.replace(hour=0, minute=0, second=0),
                    "$lt": window_end.replace(hour=23, minute=59, second=59)
                },
                "hora": {
                    "$gte": window_start.strftime("%H:%M"),
                    "$lt": window_end.strftime("%H:%M")
                },
                "estado": {"$in": ["programada", "confirmada"]}
            }).to_list(length=None)
            
            logger.info(f"Encontradas {len(appointments)} citas en ventana 2-3h")
            
            sent_count = 0
            for appointment in appointments:
                patient = await db.pacientes.find_one({"_id": appointment["paciente_id"]})
                if not patient:
                    continue
                
                preferences = await self.get_patient_preferences(str(appointment["paciente_id"]))
                
                if not preferences.get("communication_types", {}).get("appointment_reminders", True):
                    continue
                
                # Template SMS para recordatorio de 2h
                template = await self.get_template("reminder_2h", "sms")
                if not template:
                    logger.warning("Template reminder_2h no encontrado")
                    continue
                
                template_data = await self.prepare_appointment_data(appointment, patient)
                
                # Preferir SMS para recordatorio urgente
                if preferences.get("preferred_channels", {}).get("sms", True) and patient.get("telefono"):
                    result = self.sms_service.send_sms(
                        [patient["telefono"]],
                        template["text_content"],
                        template_data
                    )
                    if result and result[0].get("success"):
                        sent_count += 1
                
                # Fallback a WhatsApp
                elif preferences.get("preferred_channels", {}).get("whatsapp", True) and patient.get("telefono"):
                    # Usar servicio WhatsApp existente
                    await self.send_whatsapp(patient["telefono"], template["text_content"], template_data)
                    sent_count += 1
            
            logger.info(f"Recordatorios 2h enviados: {sent_count}")
        
        except Exception as e:
            logger.error(f"Error en recordatorios 2h: {str(e)}")
    
    async def followup_no_shows(self):
        """Seguimiento automático de pacientes que no asistieron"""
        try:
            logger.info("Ejecutando seguimiento no-shows...")
            
            # Obtener citas de ayer que no se completaron
            yesterday = datetime.now() - timedelta(days=1)
            yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = yesterday_start + timedelta(days=1)
            
            no_shows = await db.citas.find({
                "fecha": {
                    "$gte": yesterday_start,
                    "$lt": yesterday_end
                },
                "estado": {"$in": ["programada", "confirmada", "no_show"]}
            }).to_list(length=None)
            
            logger.info(f"Encontrados {len(no_shows)} no-shows de ayer")
            
            sent_count = 0
            for appointment in no_shows:
                # Verificar si ya se envió follow-up
                existing_followup = await db.communication_logs.find_one({
                    "appointment_id": str(appointment["_id"]),
                    "type": "no_show_followup"
                })
                
                if existing_followup:
                    continue
                
                patient = await db.pacientes.find_one({"_id": appointment["paciente_id"]})
                if not patient:
                    continue
                
                preferences = await self.get_patient_preferences(str(appointment["paciente_id"]))
                
                template = await self.get_template("no_show_followup", "email")
                if not template:
                    continue
                
                template_data = await self.prepare_appointment_data(appointment, patient)
                template_data["reschedule_link"] = f"https://app.rubiogarciadental.com/reschedule/{appointment['_id']}"
                
                await self.send_based_on_preferences(
                    patient,
                    template,
                    template_data,
                    preferences
                )
                
                # Registrar follow-up enviado
                await db.communication_logs.insert_one({
                    "appointment_id": str(appointment["_id"]),
                    "patient_id": str(appointment["paciente_id"]),
                    "type": "no_show_followup",
                    "sent_at": datetime.utcnow()
                })
                
                sent_count += 1
            
            logger.info(f"Follow-ups no-show enviados: {sent_count}")
        
        except Exception as e:
            logger.error(f"Error en seguimiento no-shows: {str(e)}")
    
    async def send_post_visit_messages(self):
        """Enviar mensajes de seguimiento post-visita"""
        try:
            logger.info("Ejecutando seguimiento post-visita...")
            
            # Obtener citas completadas hace 2 días
            two_days_ago = datetime.now() - timedelta(days=2)
            target_date_start = two_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)
            target_date_end = target_date_start + timedelta(days=1)
            
            completed_appointments = await db.citas.find({
                "fecha": {
                    "$gte": target_date_start,
                    "$lt": target_date_end
                },
                "estado": "completada"
            }).to_list(length=None)
            
            logger.info(f"Encontradas {len(completed_appointments)} citas completadas hace 2 días")
            
            sent_count = 0
            for appointment in completed_appointments:
                # Verificar si ya se envió post-visit
                existing_message = await db.communication_logs.find_one({
                    "appointment_id": str(appointment["_id"]),
                    "type": "post_visit"
                })
                
                if existing_message:
                    continue
                
                patient = await db.pacientes.find_one({"_id": appointment["paciente_id"]})
                if not patient:
                    continue
                
                preferences = await self.get_patient_preferences(str(appointment["paciente_id"]))
                
                template = await self.get_template("post_visit", "email")
                if not template:
                    continue
                
                template_data = await self.prepare_appointment_data(appointment, patient)
                template_data["survey_link"] = f"https://app.rubiogarciadental.com/survey/{appointment['_id']}"
                
                await self.send_based_on_preferences(
                    patient,
                    template,
                    template_data,
                    preferences
                )
                
                # Registrar mensaje enviado
                await db.communication_logs.insert_one({
                    "appointment_id": str(appointment["_id"]),
                    "patient_id": str(appointment["paciente_id"]),
                    "type": "post_visit",
                    "sent_at": datetime.utcnow()
                })
                
                sent_count += 1
            
            logger.info(f"Mensajes post-visita enviados: {sent_count}")
        
        except Exception as e:
            logger.error(f"Error en seguimiento post-visita: {str(e)}")
    
    async def send_based_on_preferences(
        self,
        patient: Dict,
        template: Dict,
        template_data: Dict,
        preferences: Dict
    ):
        """
        Enviar mensaje según preferencias del paciente
        
        Args:
            patient: Datos del paciente
            template: Template a usar
            template_data: Datos para el template
            preferences: Preferencias del paciente
        """
        preferred_channels = preferences.get("preferred_channels", {})
        
        # Email
        if preferred_channels.get("email", True) and patient.get("email") and template["type"] == "email":
            self.email_service.send_email(
                to=[patient["email"]],
                subject=template.get("subject", "Rubio García - Comunicación"),
                html_content=template["html_content"],
                text_content=template.get("text_content", ""),
                template_data=template_data
            )
        
        # SMS
        elif preferred_channels.get("sms", False) and patient.get("telefono") and template["type"] == "sms":
            self.sms_service.send_sms(
                to=[patient["telefono"]],
                message=template["text_content"],
                template_data=template_data
            )
        
        # WhatsApp
        elif preferred_channels.get("whatsapp", False) and patient.get("telefono"):
            await self.send_whatsapp(
                patient["telefono"],
                template.get("text_content", template["html_content"]),
                template_data
            )
    
    async def prepare_appointment_data(self, appointment: Dict, patient: Dict) -> Dict:
        """
        Preparar datos de cita para template
        
        Args:
            appointment: Datos de la cita
            patient: Datos del paciente
        
        Returns:
            Dict con datos formateados
        """
        # Obtener dentista
        dentist = await db.users.find_one({"_id": appointment.get("dentista_id")})
        
        return {
            "patient_name": patient.get("nombre", "Paciente"),
            "appointment_date": appointment["fecha"].strftime("%d/%m/%Y") if isinstance(appointment["fecha"], datetime) else str(appointment.get("fecha", "")),
            "appointment_time": appointment.get("hora", ""),
            "dentist_name": dentist.get("nombre", "Dr/Dra") if dentist else "Dr/Dra",
            "treatment_type": appointment.get("tratamiento", "Consulta"),
            "clinic_name": "Rubio García",
            "clinic_phone": "+34 664 218 253",
            "clinic_address": "Madrid, España",
            "clinic_email": "contacto@rubiogarciadental.com"
        }
    
    async def get_template(self, category: str, channel_type: str) -> Optional[Dict]:
        """
        Obtener template por categoría y tipo de canal
        
        Args:
            category: Categoría del template
            channel_type: Tipo de canal (email, sms, whatsapp)
        
        Returns:
            Template o None
        """
        template = await db.communication_templates.find_one({
            "category": category,
            "type": channel_type,
            "is_active": True
        })
        
        return template
    
    async def get_patient_preferences(self, patient_id: str) -> Dict:
        """
        Obtener preferencias de comunicación del paciente
        
        Args:
            patient_id: ID del paciente
        
        Returns:
            Dict con preferencias (por defecto si no existen)
        """
        preferences = await db.patient_communication_preferences.find_one({
            "patient_id": patient_id
        })
        
        if not preferences:
            # Preferencias por defecto
            return {
                "preferred_channels": {
                    "email": True,
                    "sms": True,
                    "whatsapp": True
                },
                "communication_types": {
                    "appointment_reminders": True,
                    "treatment_reminders": True,
                    "promotional_offers": False
                }
            }
        
        return preferences
    
    async def send_whatsapp(self, phone: str, message: str, template_data: Dict):
        """
        Enviar mensaje WhatsApp usando servicio existente
        
        Args:
            phone: Número de teléfono
            message: Mensaje
            template_data: Datos del template
        """
        # Procesar template
        processed_message = self.email_service.process_template(message, template_data)
        
        # Llamar al servicio WhatsApp existente (simulado en dev)
        logger.info(f"[WhatsApp] Enviando a {phone}: {processed_message[:50]}...")
        
        # En producción, hacer request al servicio WhatsApp Baileys:
        # await whatsapp_api.send_message(phone, processed_message)
