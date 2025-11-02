from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime, date
from bson import ObjectId
from app.models.patient import PyObjectId


class PatientSegment(BaseModel):
    """Segmentación de paciente para analytics"""
    value_category: Literal["alta", "media", "baja"] = Field(..., description="Categoría de valor económico")
    frequency: Literal["frecuente", "regular", "ocasional"] = Field(..., description="Frecuencia de visitas")
    loyalty_score: float = Field(..., ge=0, le=100, description="Score de lealtad 0-100")
    treatment_preference: str = Field(..., description="Tipo de tratamiento preferido")
    price_sensitivity: Literal["bajo", "medio", "alto"] = Field(..., description="Sensibilidad al precio")


class PatientAnalytics(BaseModel):
    """Analytics completo de un paciente"""
    patient_id: str = Field(..., description="ID del paciente")
    patient_name: str = Field(..., description="Nombre del paciente")
    
    # Segmentación
    segments: PatientSegment
    
    # Métricas financieras
    lifetime_value: float = Field(..., ge=0, description="Valor total histórico del paciente")
    acquisition_cost: float = Field(default=0, ge=0, description="Costo de adquisición")
    avg_transaction_value: float = Field(..., ge=0, description="Valor promedio por transacción")
    
    # Comportamiento
    total_visits: int = Field(..., ge=0, description="Total de visitas históricas")
    avg_days_between_visits: float = Field(..., ge=0, description="Días promedio entre visitas")
    retention_probability: float = Field(..., ge=0, le=100, description="Probabilidad de retención")
    churn_risk: Literal["bajo", "medio", "alto"] = Field(..., description="Riesgo de abandono")
    
    # Predicciones
    next_appointment_prediction: Optional[datetime] = Field(None, description="Fecha predicha próxima cita")
    predicted_ltv_12m: float = Field(..., ge=0, description="LTV predicho próximos 12 meses")
    
    # Metadatos
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TreatmentROI(BaseModel):
    """ROI detallado de un tratamiento"""
    treatment_name: str = Field(..., description="Nombre del tratamiento")
    
    # Ingresos
    total_revenue: float = Field(..., ge=0, description="Ingresos totales")
    avg_revenue_per_treatment: float = Field(..., ge=0, description="Ingreso promedio por tratamiento")
    
    # Costos detallados
    costs: Dict[str, float] = Field(..., description="Costos desglosados")
    total_costs: float = Field(..., ge=0, description="Costos totales")
    
    # Márgenes
    gross_profit: float = Field(..., description="Beneficio bruto")
    profit_margin_percentage: float = Field(..., description="Margen de beneficio en porcentaje")
    roi_percentage: float = Field(..., description="ROI en porcentaje")
    
    # Volumen
    total_treatments: int = Field(..., ge=0, description="Total de tratamientos realizados")
    conversion_rate: float = Field(..., ge=0, le=100, description="Tasa de conversión consulta->tratamiento")
    
    # Satisfacción
    patient_satisfaction: Optional[float] = Field(None, ge=1, le=5, description="Satisfacción promedio 1-5")


class ConversionFunnel(BaseModel):
    """Embudo de conversión de consultas a tratamientos"""
    period_start: datetime
    period_end: datetime
    
    # Etapas del funnel
    total_inquiries: int = Field(..., ge=0, description="Consultas iniciales")
    scheduled_appointments: int = Field(..., ge=0, description="Citas programadas")
    completed_appointments: int = Field(..., ge=0, description="Citas completadas")
    evaluations_done: int = Field(..., ge=0, description="Evaluaciones realizadas")
    quotes_sent: int = Field(..., ge=0, description="Presupuestos enviados")
    quotes_accepted: int = Field(..., ge=0, description="Presupuestos aceptados")
    treatments_started: int = Field(..., ge=0, description="Tratamientos iniciados")
    treatments_completed: int = Field(..., ge=0, description="Tratamientos completados")
    
    # Tasas de conversión
    inquiry_to_appointment_rate: float = Field(..., ge=0, le=100)
    appointment_to_treatment_rate: float = Field(..., ge=0, le=100)
    quote_to_treatment_rate: float = Field(..., ge=0, le=100)
    overall_conversion_rate: float = Field(..., ge=0, le=100)


class DentistPerformance(BaseModel):
    """Métricas de rendimiento de un dentista"""
    dentist_id: str = Field(..., description="ID del dentista")
    dentist_name: str = Field(..., description="Nombre del dentista")
    
    # Métricas financieras
    total_revenue: float = Field(..., ge=0, description="Ingresos totales generados")
    revenue_per_hour: float = Field(..., ge=0, description="Ingresos por hora trabajada")
    avg_treatment_value: float = Field(..., ge=0, description="Valor promedio por tratamiento")
    
    # Eficiencia
    total_hours_worked: float = Field(..., ge=0, description="Horas trabajadas totales")
    treatments_completed: int = Field(..., ge=0, description="Tratamientos completados")
    avg_treatment_duration: float = Field(..., ge=0, description="Duración promedio tratamiento (min)")
    efficiency_score: float = Field(..., ge=0, le=100, description="Score de eficiencia vs tiempo estimado")
    
    # Calidad
    treatment_success_rate: float = Field(..., ge=0, le=100, description="Tasa de éxito de tratamientos")
    patient_satisfaction: float = Field(..., ge=1, le=5, description="Satisfacción promedio pacientes")
    conversion_rate: float = Field(..., ge=0, le=100, description="Tasa conversión consulta->tratamiento")
    
    # Puntualidad
    punctuality_score: float = Field(..., ge=0, le=100, description="Porcentaje citas a tiempo")
    
    # Especialización
    top_specializations: List[Dict[str, any]] = Field(default_factory=list, description="Especializaciones principales")


class DemandForecast(BaseModel):
    """Predicción de demanda para un tratamiento"""
    treatment_name: str = Field(..., description="Nombre del tratamiento")
    
    # Datos históricos
    historical_avg_monthly: float = Field(..., ge=0, description="Promedio mensual histórico")
    
    # Predicciones
    next_month_prediction: float = Field(..., ge=0, description="Predicción próximo mes")
    next_quarter_prediction: float = Field(..., ge=0, description="Predicción próximo trimestre")
    
    # Factores
    seasonality_factor: float = Field(..., description="Factor de estacionalidad")
    trend_factor: float = Field(..., description="Factor de tendencia")
    
    # Confianza
    confidence_level: float = Field(..., ge=0, le=100, description="Nivel de confianza de la predicción")
    
    # Recomendaciones
    recommended_capacity: int = Field(..., ge=0, description="Capacidad recomendada (slots)")
    optimization_suggestions: List[str] = Field(default_factory=list)


class AnalyticsSummary(BaseModel):
    """Resumen general de analytics para dashboard"""
    period_start: datetime
    period_end: datetime
    
    # Métricas clave
    total_revenue: float = Field(..., ge=0)
    total_patients: int = Field(..., ge=0)
    new_patients: int = Field(..., ge=0)
    returning_patients: int = Field(..., ge=0)
    
    # Conversión
    overall_conversion_rate: float = Field(..., ge=0, le=100)
    conversion_rate_trend: float = Field(..., description="Tendencia % vs periodo anterior")
    
    # ROI
    avg_roi: float = Field(..., description="ROI promedio de todos los tratamientos")
    avg_profit_margin: float = Field(..., ge=0, le=100)
    
    # Satisfacción
    avg_patient_satisfaction: float = Field(..., ge=1, le=5)
    nps_score: Optional[float] = Field(None, ge=-100, le=100, description="Net Promoter Score")
    
    # Valor
    avg_ltv: float = Field(..., ge=0, description="Lifetime Value promedio")
    avg_transaction_value: float = Field(..., ge=0)
    
    # Predicciones
    revenue_forecast_next_month: float = Field(..., ge=0)
    growth_rate: float = Field(..., description="Tasa de crecimiento %")


class AnalyticsAlert(BaseModel):
    """Alerta de analytics"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    alert_type: Literal[
        "conversion_drop", 
        "roi_low", 
        "churn_risk_high", 
        "demand_surge",
        "performance_issue",
        "opportunity"
    ] = Field(..., description="Tipo de alerta")
    
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Severidad")
    
    title: str = Field(..., description="Título de la alerta")
    message: str = Field(..., description="Mensaje descriptivo")
    
    data: Dict = Field(default_factory=dict, description="Datos asociados a la alerta")
    
    action_required: bool = Field(default=False, description="Requiere acción inmediata")
    recommendations: List[str] = Field(default_factory=list, description="Recomendaciones de acción")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False, description="Alerta reconocida")
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MonthlyTrend(BaseModel):
    """Datos de tendencia mensual"""
    month: str = Field(..., description="Mes en formato YYYY-MM")
    revenue: float = Field(..., ge=0)
    patients: int = Field(..., ge=0)
    treatments: int = Field(..., ge=0)
    conversion_rate: float = Field(..., ge=0, le=100)
    satisfaction: float = Field(..., ge=1, le=5)
    roi: float = Field(...)


class ReportSchedule(BaseModel):
    """Programación de reporte automático"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    
    report_name: str = Field(..., description="Nombre del reporte")
    report_type: Literal["monthly", "weekly", "quarterly", "custom"] = Field(..., description="Tipo de reporte")
    
    # Programación
    frequency: str = Field(..., description="Frecuencia cron expression")
    recipients: List[str] = Field(..., description="Emails destinatarios")
    
    # Contenido
    include_sections: List[str] = Field(..., description="Secciones a incluir")
    format: Literal["pdf", "excel", "html"] = Field(default="pdf")
    
    # Estado
    enabled: bool = Field(default=True)
    last_generated: Optional[datetime] = None
    next_scheduled: datetime
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AnalyticsFilter(BaseModel):
    """Filtros para queries de analytics"""
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    dentist_id: Optional[str] = None
    treatment_type: Optional[str] = None
    patient_segment: Optional[str] = None
