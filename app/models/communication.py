"""
Modelos de datos para Sistema de Comunicación Automatizada
Rubio Garcia Dentapp - Email, SMS, WhatsApp
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Dict, Optional, Literal, Any
from datetime import datetime
from bson import ObjectId


# ==================== TEMPLATES ====================

class SendTiming(BaseModel):
    """Configuración de timing para envío"""
    hours_before: Optional[int] = Field(None, ge=0, le=168, description="Horas antes del evento")
    days_after: Optional[int] = Field(None, ge=0, le=30, description="Días después del evento")
    timezone: str = Field(default="Europe/Madrid", description="Zona horaria")


class PersonalizationConfig(BaseModel):
    """Configuración de personalización de templates"""
    include_clinic_logo: bool = Field(default=True, description="Incluir logo de clínica")
    include_contact_info: bool = Field(default=True, description="Incluir información de contacto")
    include_social_links: bool = Field(default=False, description="Incluir enlaces a redes sociales")
    signature: str = Field(default="El equipo de Rubio García", description="Firma del mensaje")


class CommunicationTemplate(BaseModel):
    """Template de comunicación multi-canal"""
    name: str = Field(..., min_length=3, max_length=100, description="Nombre del template")
    type: Literal["email", "sms", "whatsapp"] = Field(..., description="Tipo de canal")
    category: Literal["reminder_24h", "reminder_2h", "confirmation", "post_visit", "no_show_followup", "promotional"] = Field(
        ..., description="Categoría del mensaje"
    )
    
    # Contenido
    subject: Optional[str] = Field(None, max_length=200, description="Asunto (solo email)")
    html_content: str = Field(..., description="Contenido HTML del template")
    text_content: str = Field(..., description="Contenido texto plano (fallback)")
    
    # Variables dinámicas disponibles
    variables: List[str] = Field(
        default_factory=lambda: ["patient_name", "appointment_date", "appointment_time", "dentist_name"],
        description="Variables disponibles en el template"
    )
    
    # Configuración de envío
    send_timing: SendTiming
    
    # Personalización
    personalization: PersonalizationConfig = Field(default_factory=PersonalizationConfig)
    
    # Analytics
    tracking_enabled: bool = Field(default=True, description="Habilitar tracking de analytics")
    click_tracking: bool = Field(default=True, description="Habilitar tracking de clicks")
    
    # Estado
    is_active: bool = Field(default=True, description="Template activo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Usuario que creó el template")
    
    @validator('subject')
    def validate_subject(cls, v, values):
        if values.get('type') == 'email' and not v:
            raise ValueError("Subject es requerido para emails")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Recordatorio 24 horas",
                "type": "email",
                "category": "reminder_24h",
                "subject": "Recordatorio de cita - Rubio García",
                "html_content": "<p>Hola {{ patient_name }}, tu cita es mañana...</p>",
                "text_content": "Hola {{ patient_name }}, tu cita es mañana...",
                "variables": ["patient_name", "appointment_date"],
                "send_timing": {"hours_before": 24, "timezone": "Europe/Madrid"},
                "personalization": {"include_clinic_logo": True},
                "is_active": True,
                "created_by": "admin"
            }
        }


class CommunicationTemplateInDB(CommunicationTemplate):
    """Template en base de datos"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    class Config:
        populate_by_name = True


# ==================== CAMPAÑAS ====================

class TargetCriteria(BaseModel):
    """Criterios de targeting para campañas"""
    patient_segments: Optional[List[str]] = Field(None, description="Segmentos de pacientes")
    treatment_types: Optional[List[str]] = Field(None, description="Tipos de tratamiento")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Rango de fechas")
    dentist_id: Optional[str] = Field(None, description="ID del dentista")
    custom_filters: Optional[Dict[str, Any]] = Field(None, description="Filtros personalizados")


class ChannelConfig(BaseModel):
    """Configuración de canal para campaña"""
    type: Literal["email", "sms", "whatsapp"] = Field(..., description="Tipo de canal")
    template_id: str = Field(..., description="ID del template a usar")
    send_at: datetime = Field(..., description="Fecha y hora de envío")
    delay_hours: Optional[int] = Field(None, ge=0, description="Delay en horas desde trigger")


class CampaignAnalytics(BaseModel):
    """Analytics de campaña"""
    delivery_rate: float = Field(default=0.0, ge=0, le=100, description="Tasa de entrega %")
    open_rate: float = Field(default=0.0, ge=0, le=100, description="Tasa de apertura %")
    click_rate: float = Field(default=0.0, ge=0, le=100, description="Tasa de clicks %")
    response_rate: float = Field(default=0.0, ge=0, le=100, description="Tasa de respuesta %")
    unsubscribes: int = Field(default=0, ge=0, description="Número de bajas")
    bounces: int = Field(default=0, ge=0, description="Número de rebotes")


class CommunicationCampaign(BaseModel):
    """Campaña de comunicación"""
    name: str = Field(..., min_length=3, max_length=150, description="Nombre de la campaña")
    type: Literal["reminder", "follow_up", "promotional", "survey"] = Field(..., description="Tipo de campaña")
    
    # Targeting
    target_criteria: TargetCriteria
    
    # Canales y templates
    channels: List[ChannelConfig] = Field(..., min_items=1, description="Canales de comunicación")
    
    # Estado
    status: Literal["draft", "scheduled", "sending", "completed", "cancelled"] = Field(
        default="draft", description="Estado de la campaña"
    )
    
    # Métricas
    recipients_count: int = Field(default=0, ge=0, description="Número total de destinatarios")
    sent_count: int = Field(default=0, ge=0, description="Mensajes enviados")
    delivered_count: int = Field(default=0, ge=0, description="Mensajes entregados")
    opened_count: int = Field(default=0, ge=0, description="Mensajes abiertos")
    clicked_count: int = Field(default=0, ge=0, description="Mensajes con clicks")
    replied_count: int = Field(default=0, ge=0, description="Mensajes con respuesta")
    
    # Analytics
    analytics: CampaignAnalytics = Field(default_factory=CampaignAnalytics)
    
    # Programación
    scheduled_at: Optional[datetime] = Field(None, description="Fecha programada de envío")
    completed_at: Optional[datetime] = Field(None, description="Fecha de completación")
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Usuario creador")


class CommunicationCampaignInDB(CommunicationCampaign):
    """Campaña en base de datos"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    class Config:
        populate_by_name = True


# ==================== PREFERENCIAS DE PACIENTE ====================

class PreferredChannels(BaseModel):
    """Canales preferidos del paciente"""
    email: bool = Field(default=True, description="Recibir emails")
    sms: bool = Field(default=True, description="Recibir SMS")
    whatsapp: bool = Field(default=True, description="Recibir WhatsApp")
    phone_call: bool = Field(default=False, description="Recibir llamadas")


class PreferredTimes(BaseModel):
    """Horarios preferidos para recibir comunicaciones"""
    morning_start: str = Field(default="09:00", description="Inicio mañana")
    morning_end: str = Field(default="12:00", description="Fin mañana")
    afternoon_start: str = Field(default="16:00", description="Inicio tarde")
    afternoon_end: str = Field(default="20:00", description="Fin tarde")
    timezone: str = Field(default="Europe/Madrid", description="Zona horaria")


class CommunicationTypes(BaseModel):
    """Tipos de comunicación aceptadas"""
    appointment_reminders: bool = Field(default=True, description="Recordatorios de citas")
    treatment_reminders: bool = Field(default=True, description="Recordatorios de tratamientos")
    promotional_offers: bool = Field(default=False, description="Ofertas promocionales")
    health_tips: bool = Field(default=True, description="Consejos de salud")
    survey_requests: bool = Field(default=True, description="Encuestas")


class QuietHours(BaseModel):
    """Horas de silencio (no enviar mensajes)"""
    start: str = Field(default="22:00", description="Inicio horas de silencio")
    end: str = Field(default="08:00", description="Fin horas de silencio")


class FrequencyLimits(BaseModel):
    """Límites de frecuencia de comunicaciones"""
    max_sms_per_week: int = Field(default=3, ge=0, le=20, description="SMS máximos por semana")
    max_emails_per_week: int = Field(default=5, ge=0, le=30, description="Emails máximos por semana")
    quiet_hours: QuietHours = Field(default_factory=QuietHours)


class PatientCommunicationPreferences(BaseModel):
    """Preferencias de comunicación del paciente"""
    patient_id: str = Field(..., description="ID del paciente")
    
    # Canales
    preferred_channels: PreferredChannels = Field(default_factory=PreferredChannels)
    
    # Horarios
    preferred_times: PreferredTimes = Field(default_factory=PreferredTimes)
    
    # Tipos de comunicación
    communication_types: CommunicationTypes = Field(default_factory=CommunicationTypes)
    
    # Límites de frecuencia
    frequency_limits: FrequencyLimits = Field(default_factory=FrequencyLimits)
    
    # Idioma
    language_preference: Literal["es", "en", "other"] = Field(default="es", description="Idioma preferido")
    
    # Metadatos
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="system", description="Usuario que actualizó")


class PatientCommunicationPreferencesInDB(PatientCommunicationPreferences):
    """Preferencias en base de datos"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    class Config:
        populate_by_name = True


# ==================== ANALYTICS ====================

class ChannelMetrics(BaseModel):
    """Métricas por canal"""
    sent: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    opened: int = Field(default=0, ge=0)
    clicked: int = Field(default=0, ge=0)
    bounced: int = Field(default=0, ge=0)
    unsubscribed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class EmailMetrics(ChannelMetrics):
    """Métricas específicas de email"""
    pass


class SMSMetrics(BaseModel):
    """Métricas específicas de SMS"""
    sent: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    clicked: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)


class WhatsAppMetrics(BaseModel):
    """Métricas específicas de WhatsApp"""
    sent: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    read: int = Field(default=0, ge=0)
    replied: int = Field(default=0, ge=0)


class AllChannelMetrics(BaseModel):
    """Métricas de todos los canales"""
    email: EmailMetrics = Field(default_factory=EmailMetrics)
    sms: SMSMetrics = Field(default_factory=SMSMetrics)
    whatsapp: WhatsAppMetrics = Field(default_factory=WhatsAppMetrics)


class TemplatePerformance(BaseModel):
    """Performance de un template"""
    template_id: str
    template_name: str
    type: str
    sent: int = Field(default=0, ge=0)
    open_rate: float = Field(default=0.0, ge=0, le=100)
    click_rate: float = Field(default=0.0, ge=0, le=100)
    response_rate: float = Field(default=0.0, ge=0, le=100)


class TrendDataPoint(BaseModel):
    """Punto de datos para tendencias"""
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    sent: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    opened: int = Field(default=0, ge=0)


class TopResponder(BaseModel):
    """Paciente con alta interacción"""
    patient_id: str
    patient_name: str
    total_interactions: int = Field(ge=0)
    last_interaction: datetime


class CommunicationAnalytics(BaseModel):
    """Analytics completo del sistema de comunicación"""
    
    # Métricas globales
    global_metrics: Dict[str, int] = Field(
        default_factory=lambda: {
            "total_sent": 0,
            "total_delivered": 0,
            "total_opened": 0,
            "total_clicked": 0,
            "total_replied": 0
        }
    )
    
    # Métricas por canal
    channel_metrics: AllChannelMetrics = Field(default_factory=AllChannelMetrics)
    
    # Performance de templates
    template_performance: List[TemplatePerformance] = Field(default_factory=list)
    
    # Tendencias temporales
    trends: List[TrendDataPoint] = Field(default_factory=list)
    
    # Pacientes más activos
    top_responders: List[TopResponder] = Field(default_factory=list)


# ==================== CONFIGURACIÓN DE SERVICIOS ====================

class SMTPConfig(BaseModel):
    """Configuración SMTP para emails"""
    server: str = Field(..., description="Servidor SMTP (ej: smtp.gmail.com)")
    port: int = Field(..., ge=1, le=65535, description="Puerto SMTP (587, 465, etc.)")
    username: str = Field(..., description="Usuario/email SMTP")
    password: str = Field(..., description="Contraseña SMTP")
    use_tls: bool = Field(default=True, description="Usar TLS")
    from_name: str = Field(default="Rubio García", description="Nombre del remitente")
    from_email: EmailStr = Field(..., description="Email del remitente")


class TwilioConfig(BaseModel):
    """Configuración de Twilio para SMS"""
    account_sid: str = Field(..., description="Account SID de Twilio")
    auth_token: str = Field(..., description="Auth Token de Twilio")
    from_number: str = Field(..., description="Número de teléfono Twilio (formato +34XXXXXXXXX)")
    
    @validator('from_number')
    def validate_phone(cls, v):
        if not v.startswith('+'):
            raise ValueError("El número debe incluir el código de país con +")
        return v


class WhatsAppConfig(BaseModel):
    """Configuración de WhatsApp (usa servicio existente)"""
    service_url: str = Field(default="http://localhost:3001", description="URL del servicio WhatsApp Baileys")
    timeout: int = Field(default=30, ge=5, le=120, description="Timeout en segundos")


class CommunicationConfig(BaseModel):
    """Configuración general del sistema de comunicación"""
    smtp: Optional[SMTPConfig] = None
    twilio: Optional[TwilioConfig] = None
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    
    # Configuración general
    default_timezone: str = Field(default="Europe/Madrid")
    enable_auto_reminders: bool = Field(default=True, description="Habilitar recordatorios automáticos")
    enable_no_show_followup: bool = Field(default=True, description="Habilitar seguimiento de no-shows")
    
    # Límites globales
    daily_email_limit: int = Field(default=1000, ge=0, description="Límite diario de emails")
    daily_sms_limit: int = Field(default=500, ge=0, description="Límite diario de SMS")
    
    # Metadatos
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = Field(default="admin")


class CommunicationConfigInDB(CommunicationConfig):
    """Configuración en base de datos"""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    
    class Config:
        populate_by_name = True
