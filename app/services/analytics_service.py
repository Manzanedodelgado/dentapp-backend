"""
Servicios de analytics empresarial para Rubio Garcia Dentapp
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import statistics
from app.models.analytics import (
    PatientAnalytics, PatientSegment, TreatmentROI,
    ConversionFunnel, DentistPerformance, AnalyticsSummary,
    DemandForecast, MonthlyTrend
)


# ==================== EXPORTS FOR ROUTES ====================
# Estas funciones se exportan para compatibilidad con las rutas

async def calculate_patient_ltv(patient_id: str, db) -> float:
    """Export function for calculate_patient_ltv"""
    return await AnalyticsService.calculate_patient_ltv(patient_id, db)

async def analyze_patient_segments(db) -> List[PatientSegment]:
    """Export function for analyze_patient_segments"""
    return await AnalyticsService.analyze_patient_segments(db)

async def calculate_conversion_rate(db) -> float:
    """Export function for calculate_conversion_rate"""
    return await AnalyticsService.calculate_conversion_rate(db)

async def calculate_treatment_roi(treatment_name: str, db) -> TreatmentROI:
    """Export function for calculate_treatment_roi"""
    return await AnalyticsService.calculate_treatment_roi(treatment_name, db)

async def analyze_dentist_performance(dentist_id: str, db) -> DentistPerformance:
    """Export function for analyze_dentist_performance"""
    return await AnalyticsService.analyze_dentist_performance(dentist_id, db)

async def predict_demand(months_ahead: int, db) -> DemandForecast:
    """Export function for predict_demand"""
    return await AnalyticsService.predict_demand(months_ahead, db)

async def calculate_churn_risk(patient_id: str, db) -> str:
    """Export function for calculate_churn_risk"""
    return await AnalyticsService.calculate_churn_risk(patient_id, db)

async def analyze_conversion_funnel(period_start: datetime, period_end: datetime, db) -> ConversionFunnel:
    """Export function for analyze_conversion_funnel"""
    return await AnalyticsService.analyze_conversion_funnel(period_start, period_end, db)class AnalyticsService:
    """Servicios principales de analytics"""
    
    @staticmethod
    async def calculate_patient_ltv(patient_id: str, db) -> float:
        """Calcular Lifetime Value de un paciente"""
        # Obtener todas las facturas del paciente
        facturas = await db.facturas.find({
            "receptor.nombre_completo": {"$exists": True},
            "estado": {"$in": ["emitida", "pagada"]}
        }).to_list(length=None)
        
        # Filtrar por paciente (comparar por ID si está disponible)
        patient = await db.patients.find_one({"_id": patient_id})
        if not patient:
            return 0
        
        patient_facturas = [
            f for f in facturas 
            if f.get("receptor", {}).get("nombre_completo") == patient.get("name")
        ]
        
        ltv = sum(f.get("total_factura", 0) for f in patient_facturas)
        return round(ltv, 2)
    
    @staticmethod
    async def calculate_patient_analytics(patient_id: str, db) -> PatientAnalytics:
        """Calcular analytics completo de un paciente"""
        
        patient = await db.patients.find_one({"_id": patient_id})
        if not patient:
            raise ValueError("Paciente no encontrado")
        
        # Obtener citas del paciente
        appointments = await db.appointments.find({
            "patient_id": str(patient_id)
        }).to_list(length=None)
        
        total_visits = len(appointments)
        
        # Calcular LTV
        ltv = await AnalyticsService.calculate_patient_ltv(patient_id, db)
        
        # Frecuencia de visitas
        if total_visits >= 2:
            # Ordenar por fecha
            sorted_appointments = sorted(
                appointments, 
                key=lambda x: x.get("date", datetime.min)
            )
            
            # Calcular días entre visitas
            days_between = []
            for i in range(1, len(sorted_appointments)):
                delta = sorted_appointments[i]["date"] - sorted_appointments[i-1]["date"]
                days_between.append(delta.days)
            
            avg_days = statistics.mean(days_between) if days_between else 0
        else:
            avg_days = 0
        
        # Segmentación
        segment = AnalyticsService._classify_patient_segment(ltv, total_visits, avg_days)
        
        # Predicción próxima cita
        next_appointment_pred = None
        if avg_days > 0 and appointments:
            last_appointment = max(appointments, key=lambda x: x.get("date", datetime.min))
            next_appointment_pred = last_appointment["date"] + timedelta(days=avg_days)
        
        # Cálculo de churn risk
        churn_risk = AnalyticsService._calculate_churn_risk(
            total_visits, avg_days, appointments
        )
        
        # Valor promedio por transacción
        avg_transaction = ltv / total_visits if total_visits > 0 else 0
        
        # Probabilidad de retención (simplificado)
        retention_probability = 100 - (churn_risk_score := {
            "bajo": 10,
            "medio": 40,
            "alto": 75
        }.get(churn_risk, 50))
        
        # Predicción LTV 12 meses
        predicted_ltv_12m = AnalyticsService._predict_ltv_12m(
            ltv, total_visits, avg_days
        )
        
        return PatientAnalytics(
            patient_id=str(patient_id),
            patient_name=patient.get("name", "Unknown"),
            segments=segment,
            lifetime_value=ltv,
            acquisition_cost=0,  # Puede configurarse
            avg_transaction_value=round(avg_transaction, 2),
            total_visits=total_visits,
            avg_days_between_visits=round(avg_days, 1),
            retention_probability=round(retention_probability, 1),
            churn_risk=churn_risk,
            next_appointment_prediction=next_appointment_pred,
            predicted_ltv_12m=round(predicted_ltv_12m, 2)
        )
    
    @staticmethod
    def _classify_patient_segment(ltv: float, visits: int, avg_days: float) -> PatientSegment:
        """Clasificar paciente en segmento"""
        
        # Categoría de valor
        if ltv >= 2000:
            value_cat = "alta"
        elif ltv >= 500:
            value_cat = "media"
        else:
            value_cat = "baja"
        
        # Frecuencia
        if avg_days > 0 and avg_days <= 90:
            frequency = "frecuente"
        elif avg_days <= 180:
            frequency = "regular"
        else:
            frequency = "ocasional"
        
        # Loyalty score (basado en visitas y valor)
        loyalty_score = min(100, (visits * 10) + (ltv / 50))
        
        # Preferencia de tratamiento (simplificado)
        treatment_pref = "general"
        
        # Sensibilidad al precio (basado en valor promedio)
        avg_value = ltv / visits if visits > 0 else 0
        if avg_value >= 200:
            price_sens = "bajo"
        elif avg_value >= 80:
            price_sens = "medio"
        else:
            price_sens = "alto"
        
        return PatientSegment(
            value_category=value_cat,
            frequency=frequency,
            loyalty_score=round(loyalty_score, 1),
            treatment_preference=treatment_pref,
            price_sensitivity=price_sens
        )
    
    @staticmethod
    def _calculate_churn_risk(visits: int, avg_days: float, appointments: List) -> str:
        """Calcular riesgo de abandono"""
        
        if not appointments:
            return "alto"
        
        # Última cita
        last_appointment = max(appointments, key=lambda x: x.get("date", datetime.min))
        days_since_last = (datetime.utcnow() - last_appointment["date"]).days
        
        # Riesgo basado en tiempo desde última visita
        if avg_days > 0:
            ratio = days_since_last / avg_days
            if ratio > 2:
                return "alto"
            elif ratio > 1.5:
                return "medio"
        
        # Riesgo por pocas visitas
        if visits < 3:
            return "medio"
        
        return "bajo"
    
    @staticmethod
    def _predict_ltv_12m(current_ltv: float, visits: int, avg_days: float) -> float:
        """Predecir LTV próximos 12 meses"""
        
        if visits == 0 or avg_days == 0:
            return 0
        
        # Calcular visitas esperadas en 12 meses
        expected_visits_12m = 365 / avg_days if avg_days > 0 else 0
        
        # Valor promedio por visita
        avg_per_visit = current_ltv / visits
        
        # Predicción
        predicted = expected_visits_12m * avg_per_visit
        
        return predicted
    
    @staticmethod
    async def calculate_treatment_roi(treatment_name: str, db) -> TreatmentROI:
        """Calcular ROI detallado de un tratamiento"""
        
        # Obtener facturas de este tratamiento
        facturas = await db.facturas.find({
            "estado": {"$in": ["emitida", "pagada"]}
        }).to_list(length=None)
        
        # Filtrar por tratamiento
        treatment_facturas = []
        for factura in facturas:
            for linea in factura.get("lineas", []):
                if treatment_name.lower() in linea.get("concepto", "").lower():
                    treatment_facturas.append((factura, linea))
        
        if not treatment_facturas:
            raise ValueError("No hay datos de este tratamiento")
        
        # Calcular ingresos
        total_revenue = sum(linea.get("total_linea", 0) for _, linea in treatment_facturas)
        total_treatments = len(treatment_facturas)
        avg_revenue = total_revenue / total_treatments if total_treatments > 0 else 0
        
        # Calcular costos (simplificado - pueden configurarse)
        material_costs = total_revenue * 0.15  # 15% materiales
        dentist_time_cost = total_revenue * 0.25  # 25% tiempo dentista
        overhead_costs = total_revenue * 0.10  # 10% overhead
        
        total_costs = material_costs + dentist_time_cost + overhead_costs
        
        # Calcular márgenes
        gross_profit = total_revenue - total_costs
        profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
        roi = (gross_profit / total_costs * 100) if total_costs > 0 else 0
        
        # Conversión (simplificado - requeriría más datos)
        conversion_rate = 65.0  # Placeholder
        
        return TreatmentROI(
            treatment_name=treatment_name,
            total_revenue=round(total_revenue, 2),
            avg_revenue_per_treatment=round(avg_revenue, 2),
            costs={
                "materials": round(material_costs, 2),
                "dentist_time": round(dentist_time_cost, 2),
                "overhead": round(overhead_costs, 2)
            },
            total_costs=round(total_costs, 2),
            gross_profit=round(gross_profit, 2),
            profit_margin_percentage=round(profit_margin, 2),
            roi_percentage=round(roi, 2),
            total_treatments=total_treatments,
            conversion_rate=conversion_rate,
            patient_satisfaction=4.5  # Placeholder
        )
    
    @staticmethod
    async def calculate_conversion_funnel(
        period_start: datetime, 
        period_end: datetime, 
        db
    ) -> ConversionFunnel:
        """Calcular embudo de conversión"""
        
        # Obtener citas en el periodo
        appointments = await db.appointments.find({
            "date": {
                "$gte": period_start,
                "$lte": period_end
            }
        }).to_list(length=None)
        
        total_appointments = len(appointments)
        completed = len([a for a in appointments if a.get("status") == "completed"])
        
        # Obtener facturas del periodo
        facturas = await db.facturas.find({
            "fecha_emision": {
                "$gte": period_start,
                "$lte": period_end
            },
            "estado": {"$in": ["emitida", "pagada"]}
        }).to_list(length=None)
        
        total_facturas = len(facturas)
        
        # Calcular etapas (simplificado)
        total_inquiries = int(total_appointments * 1.5)  # Estimado
        scheduled = total_appointments
        completed_appts = completed
        evaluations = int(completed * 0.8)
        quotes_sent = int(evaluations * 0.9)
        quotes_accepted = total_facturas
        treatments_started = total_facturas
        treatments_completed = int(total_facturas * 0.95)
        
        # Tasas de conversión
        inquiry_to_appt = (scheduled / total_inquiries * 100) if total_inquiries > 0 else 0
        appt_to_treatment = (treatments_started / completed_appts * 100) if completed_appts > 0 else 0
        quote_to_treatment = (quotes_accepted / quotes_sent * 100) if quotes_sent > 0 else 0
        overall = (treatments_completed / total_inquiries * 100) if total_inquiries > 0 else 0
        
        return ConversionFunnel(
            period_start=period_start,
            period_end=period_end,
            total_inquiries=total_inquiries,
            scheduled_appointments=scheduled,
            completed_appointments=completed_appts,
            evaluations_done=evaluations,
            quotes_sent=quotes_sent,
            quotes_accepted=quotes_accepted,
            treatments_started=treatments_started,
            treatments_completed=treatments_completed,
            inquiry_to_appointment_rate=round(inquiry_to_appt, 2),
            appointment_to_treatment_rate=round(appt_to_treatment, 2),
            quote_to_treatment_rate=round(quote_to_treatment, 2),
            overall_conversion_rate=round(overall, 2)
        )
    
    @staticmethod
    async def calculate_dentist_performance(dentist_id: str, db) -> DentistPerformance:
        """Calcular métricas de rendimiento de un dentista"""
        
        # Obtener citas del dentista
        appointments = await db.appointments.find({
            "doctor": dentist_id
        }).to_list(length=None)
        
        total_appts = len(appointments)
        completed = [a for a in appointments if a.get("status") == "completed"]
        
        # Calcular ingresos (via facturas - simplificado)
        # En un sistema real, vincularíamos facturas con dentista
        total_revenue = total_appts * 120  # Estimado
        
        # Horas trabajadas (estimado)
        total_hours = total_appts * 0.75  # 45min promedio
        revenue_per_hour = total_revenue / total_hours if total_hours > 0 else 0
        
        # Eficiencia
        on_time = len([a for a in appointments if True])  # Simplificado
        punctuality = (on_time / total_appts * 100) if total_appts > 0 else 0
        
        return DentistPerformance(
            dentist_id=dentist_id,
            dentist_name=dentist_id.capitalize(),
            total_revenue=round(total_revenue, 2),
            revenue_per_hour=round(revenue_per_hour, 2),
            avg_treatment_value=round(total_revenue / total_appts, 2) if total_appts > 0 else 0,
            total_hours_worked=round(total_hours, 2),
            treatments_completed=len(completed),
            avg_treatment_duration=45.0,
            efficiency_score=85.0,
            treatment_success_rate=95.0,
            patient_satisfaction=4.6,
            conversion_rate=67.0,
            punctuality_score=round(punctuality, 2),
            top_specializations=[]
        )
    
    @staticmethod
    async def calculate_analytics_summary(
        period_start: datetime,
        period_end: datetime,
        db
    ) -> AnalyticsSummary:
        """Calcular resumen general de analytics"""
        
        # Facturas del periodo
        facturas = await db.facturas.find({
            "fecha_emision": {
                "$gte": period_start,
                "$lte": period_end
            },
            "estado": {"$in": ["emitida", "pagada"]}
        }).to_list(length=None)
        
        total_revenue = sum(f.get("total_factura", 0) for f in facturas)
        
        # Pacientes
        all_patients = await db.patients.find({}).to_list(length=None)
        total_patients = len(all_patients)
        
        # Nuevos pacientes en el periodo
        new_patients = len([
            p for p in all_patients 
            if period_start <= p.get("created_at", datetime.min) <= period_end
        ])
        
        returning_patients = total_patients - new_patients
        
        # Conversión
        funnel = await AnalyticsService.calculate_conversion_funnel(
            period_start, period_end, db
        )
        
        return AnalyticsSummary(
            period_start=period_start,
            period_end=period_end,
            total_revenue=round(total_revenue, 2),
            total_patients=total_patients,
            new_patients=new_patients,
            returning_patients=returning_patients,
            overall_conversion_rate=funnel.overall_conversion_rate,
            conversion_rate_trend=5.2,  # Placeholder
            avg_roi=135.0,  # Placeholder
            avg_profit_margin=45.0,  # Placeholder
            avg_patient_satisfaction=4.6,
            nps_score=72.0,
            avg_ltv=850.0,  # Placeholder
            avg_transaction_value=round(total_revenue / len(facturas), 2) if facturas else 0,
            revenue_forecast_next_month=round(total_revenue * 1.1, 2),
            growth_rate=8.5  # Placeholder
        )
    
    @staticmethod
    async def analyze_patient_segments(db) -> List[PatientSegment]:
        """Analizar segmentos de pacientes"""
        patients = await db.patients.find({}).to_list(length=None)
        segments = []
        
        # Obtener analytics de cada paciente
        for patient in patients:
            patient_id = str(patient["_id"])
            analytics = await AnalyticsService.calculate_patient_analytics(patient_id, db)
            
            segment = PatientSegment(
                patient_id=patient_id,
                segment_name=analytics.segment_name,
                segment_value=analytics.segment_value,
                ltv=analytics.ltv,
                visit_frequency=analytics.visit_frequency,
                churn_risk=analytics.churn_risk,
                recommended_actions=analytics.recommended_actions
            )
            segments.append(segment)
        
        return segments
    
    @staticmethod
    async def calculate_conversion_rate(db) -> float:
        """Calcular tasa de conversión general"""
        # Obtener conversiones del embudo
        funnel = await AnalyticsService.calculate_conversion_funnel(
            datetime.now() - timedelta(days=30), datetime.now(), db
        )
        return funnel.overall_conversion_rate
    
    @staticmethod
    async def predict_demand(months_ahead: int, db) -> DemandForecast:
        """Predecir demanda futura"""
        # Obtener datos históricos de citas
        historic_appointments = await db.appointments.find({
            "date": {
                "$gte": datetime.now() - timedelta(days=365),
                "$lte": datetime.now()
            }
        }).to_list(length=None)
        
        # Predicción simple basada en tendencias
        monthly_demand = len(historic_appointments) / 12
        predicted_demand = monthly_demand * (1 + 0.05) ** months_ahead  # 5% crecimiento
        
        return DemandForecast(
            predicted_demand=round(predicted_demand),
            confidence_level=0.75,
            trend_direction="upward",
            seasonal_factors={
                "enero": 1.0,
                "febrero": 0.9,
                "marzo": 1.1,
                "abril": 1.0,
                "mayo": 1.0,
                "junio": 0.8,
                "julio": 0.7,
                "agosto": 0.6,
                "septiembre": 1.1,
                "octubre": 1.2,
                "noviembre": 1.1,
                "diciembre": 0.9
            }
        )
    
    @staticmethod
    async def calculate_churn_risk(patient_id: str, db) -> str:
        """Calcular riesgo de churn"""
        analytics = await AnalyticsService.calculate_patient_analytics(patient_id, db)
        return analytics.churn_risk
    
    @staticmethod
    async def analyze_conversion_funnel(
        period_start: datetime, period_end: datetime, db
    ) -> ConversionFunnel:
        """Analizar embudo de conversión"""
        # Obtener consultas y tratamientos del periodo
        appointments = await db.appointments.find({
            "date": {
                "$gte": period_start,
                "$lte": period_end
            }
        }).to_list(length=None)
        
        total_inquiries = len(appointments)
        consultations = len([a for a in appointments if a.get("status") == "completada"])
        treatments = len([a for a in appointments if a.get("treatment_name")])
        
        return ConversionFunnel(
            period_start=period_start,
            period_end=period_end,
            total_inquiries=total_inquiries,
            consultations=consultations,
            treatments=treatments,
            consultation_conversion_rate=(consultations / total_inquiries * 100) if total_inquiries > 0 else 0,
            treatment_conversion_rate=(treatments / consultations * 100) if consultations > 0 else 0,
            overall_conversion_rate=(treatments / total_inquiries * 100) if total_inquiries > 0 else 0
        )
    
    @staticmethod
    async def analyze_dentist_performance(dentist_id: str, db) -> DentistPerformance:
        """Analizar rendimiento de dentista"""
        # Obtener citas del dentista
        appointments = await db.appointments.find({
            "dentist_id": dentist_id
        }).to_list(length=None)
        
        total_appointments = len(appointments)
        completed_appointments = len([a for a in appointments if a.get("status") == "completada"])
        
        return DentistPerformance(
            dentist_id=dentist_id,
            total_appointments=total_appointments,
            completed_appointments=completed_appointments,
            completion_rate=(completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            avg_appointment_duration=30.0,  # Placeholder
            patient_satisfaction_score=4.5,
            revenue_generated=2500.0  # Placeholder
        )
        )
