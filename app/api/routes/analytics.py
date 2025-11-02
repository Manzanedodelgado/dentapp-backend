"""
Rutas API para Analytics Avanzado - Rubio Garcia Dentapp
Sistema de análisis empresarial con predicciones ML y ROI detallado
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from ...database import db
from ...models.analytics import (
    PatientSegment,
    PatientAnalytics,
    TreatmentAnalytics,
    TreatmentROI,
    DentistPerformance,
    MonthlyTrend,
    PredictionData
)
from ...services.analytics_service import (
    calculate_patient_ltv,
    analyze_patient_segments,
    calculate_conversion_rate,
    calculate_treatment_roi,
    analyze_dentist_performance,
    predict_demand,
    calculate_churn_risk,
    analyze_conversion_funnel
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ==================== OVERVIEW & DASHBOARD ====================

@router.get("/overview")
async def get_analytics_overview(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene resumen general de analytics con KPIs principales
    """
    try:
        # Parsear fechas
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            # Últimos 30 días por defecto
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        # Obtener datos básicos
        pacientes_count = await db.pacientes.count_documents({})
        facturas_periodo = await db.facturas.count_documents({
            "fecha_emision": {"$gte": inicio, "$lte": fin}
        })
        
        # Calcular ingresos del período
        pipeline_ingresos = [
            {"$match": {"fecha_emision": {"$gte": inicio, "$lte": fin}, "estado": {"$in": ["emitida", "pagada"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        ingresos_result = await db.facturas.aggregate(pipeline_ingresos).to_list(length=1)
        ingresos_total = ingresos_result[0]["total"] if ingresos_result else 0
        
        # Calcular tasa de conversión
        conversion_data = await analyze_conversion_funnel(inicio, fin)
        
        # Obtener top tratamientos
        pipeline_tratamientos = [
            {"$match": {"fecha": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": "$tratamiento",
                "count": {"$sum": 1},
                "ingresos": {"$sum": "$costo"}
            }},
            {"$sort": {"ingresos": -1}},
            {"$limit": 5}
        ]
        top_tratamientos = await db.citas.aggregate(pipeline_tratamientos).to_list(length=5)
        
        # Tendencia mensual
        pipeline_tendencia = [
            {"$match": {"fecha_emision": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$fecha_emision"},
                    "month": {"$month": "$fecha_emision"}
                },
                "ingresos": {"$sum": "$total"},
                "facturas": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        tendencia = await db.facturas.aggregate(pipeline_tendencia).to_list(length=12)
        
        return {
            "periodo": {
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat()
            },
            "kpis": {
                "total_pacientes": pacientes_count,
                "facturas_emitidas": facturas_periodo,
                "ingresos_total": round(ingresos_total, 2),
                "ticket_promedio": round(ingresos_total / facturas_periodo, 2) if facturas_periodo > 0 else 0,
                "tasa_conversion": conversion_data.get("tasa_global", 0)
            },
            "top_tratamientos": [
                {
                    "tratamiento": t["_id"],
                    "cantidad": t["count"],
                    "ingresos": round(t["ingresos"], 2)
                }
                for t in top_tratamientos
            ],
            "tendencia_mensual": [
                {
                    "mes": f"{t['_id']['year']}-{t['_id']['month']:02d}",
                    "ingresos": round(t["ingresos"], 2),
                    "facturas": t["facturas"]
                }
                for t in tendencia
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo overview: {str(e)}")


# ==================== ANÁLISIS DE PACIENTES ====================

@router.get("/pacientes/segmentos")
async def get_patient_segments():
    """
    Obtiene segmentación de pacientes por valor, frecuencia y lealtad
    """
    try:
        segments = await analyze_patient_segments()
        return {"segmentos": segments}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en segmentación: {str(e)}")


@router.get("/pacientes/{paciente_id}/analytics")
async def get_patient_analytics(paciente_id: str):
    """
    Obtiene analytics detallado de un paciente específico
    """
    try:
        # Validar ObjectId
        if not ObjectId.is_valid(paciente_id):
            raise HTTPException(status_code=400, detail="ID de paciente inválido")
        
        # Verificar existencia
        paciente = await db.pacientes.find_one({"_id": ObjectId(paciente_id)})
        if not paciente:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        # Calcular LTV
        ltv = await calculate_patient_ltv(paciente_id)
        
        # Obtener historial de facturas
        facturas = await db.facturas.find(
            {"paciente_id": ObjectId(paciente_id)},
            {"fecha_emision": 1, "total": 1, "estado": 1}
        ).sort("fecha_emision", -1).to_list(length=None)
        
        # Calcular riesgo de abandono
        churn_risk = await calculate_churn_risk(paciente_id)
        
        # Obtener tratamientos realizados
        tratamientos = await db.citas.find(
            {"paciente_id": ObjectId(paciente_id), "estado": "completada"},
            {"fecha": 1, "tratamiento": 1, "costo": 1}
        ).sort("fecha", -1).to_list(length=None)
        
        return {
            "paciente_id": paciente_id,
            "nombre": paciente.get("nombre", ""),
            "lifetime_value": round(ltv, 2),
            "riesgo_abandono": churn_risk,
            "total_facturas": len(facturas),
            "total_gastado": sum(f.get("total", 0) for f in facturas),
            "tratamientos_realizados": len(tratamientos),
            "ultima_visita": tratamientos[0]["fecha"].isoformat() if tratamientos else None,
            "historial_facturas": [
                {
                    "fecha": f["fecha_emision"].isoformat(),
                    "total": f["total"],
                    "estado": f["estado"]
                }
                for f in facturas[:10]  # Últimas 10
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo analytics de paciente: {str(e)}")


@router.get("/pacientes/ltv/ranking")
async def get_ltv_ranking(limit: int = Query(20, ge=1, le=100)):
    """
    Obtiene ranking de pacientes por Lifetime Value
    """
    try:
        # Agregar facturas por paciente
        pipeline = [
            {"$match": {"estado": {"$in": ["emitida", "pagada"]}}},
            {"$group": {
                "_id": "$paciente_id",
                "total_gastado": {"$sum": "$total"},
                "num_facturas": {"$sum": 1}
            }},
            {"$sort": {"total_gastado": -1}},
            {"$limit": limit}
        ]
        
        ranking_data = await db.facturas.aggregate(pipeline).to_list(length=limit)
        
        # Obtener información de pacientes
        ranking = []
        for item in ranking_data:
            paciente = await db.pacientes.find_one({"_id": item["_id"]})
            if paciente:
                ranking.append({
                    "paciente_id": str(item["_id"]),
                    "nombre": paciente.get("nombre", ""),
                    "email": paciente.get("email", ""),
                    "telefono": paciente.get("telefono", ""),
                    "lifetime_value": round(item["total_gastado"], 2),
                    "num_visitas": item["num_facturas"]
                })
        
        return {"ranking": ranking}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo ranking LTV: {str(e)}")


# ==================== ANÁLISIS DE CONVERSIONES ====================

@router.get("/conversiones/funnel")
async def get_conversion_funnel(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene análisis del embudo de conversión
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        funnel_data = await analyze_conversion_funnel(inicio, fin)
        return funnel_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de funnel: {str(e)}")


@router.get("/conversiones/por-tratamiento")
async def get_conversion_by_treatment(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene tasa de conversión por tipo de tratamiento
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        # Consultas por tratamiento
        consultas_pipeline = [
            {"$match": {
                "fecha": {"$gte": inicio, "$lte": fin},
                "tipo": "consulta"
            }},
            {"$group": {
                "_id": "$tratamiento",
                "consultas": {"$sum": 1}
            }}
        ]
        consultas = await db.citas.aggregate(consultas_pipeline).to_list(length=None)
        consultas_dict = {c["_id"]: c["consultas"] for c in consultas}
        
        # Tratamientos completados
        tratamientos_pipeline = [
            {"$match": {
                "fecha": {"$gte": inicio, "$lte": fin},
                "estado": "completada"
            }},
            {"$group": {
                "_id": "$tratamiento",
                "tratamientos": {"$sum": 1},
                "ingresos": {"$sum": "$costo"}
            }}
        ]
        tratamientos = await db.citas.aggregate(tratamientos_pipeline).to_list(length=None)
        
        # Calcular conversiones
        conversiones = []
        for t in tratamientos:
            tratamiento = t["_id"]
            consultas_count = consultas_dict.get(tratamiento, 0)
            tratamientos_count = t["tratamientos"]
            
            tasa = (tratamientos_count / consultas_count * 100) if consultas_count > 0 else 0
            
            conversiones.append({
                "tratamiento": tratamiento,
                "consultas": consultas_count,
                "conversiones": tratamientos_count,
                "tasa_conversion": round(tasa, 2),
                "ingresos_generados": round(t["ingresos"], 2)
            })
        
        # Ordenar por tasa de conversión
        conversiones.sort(key=lambda x: x["tasa_conversion"], reverse=True)
        
        return {"conversiones_por_tratamiento": conversiones}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en conversión por tratamiento: {str(e)}")


# ==================== ROI DETALLADO ====================

@router.get("/roi/tratamientos")
async def get_treatment_roi(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene ROI detallado por tratamiento
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=90)
        
        roi_data = await calculate_treatment_roi(inicio, fin)
        return {"roi_tratamientos": roi_data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando ROI: {str(e)}")


@router.get("/roi/dentistas")
async def get_dentist_performance(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene rendimiento y ROI por dentista
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        performance_data = await analyze_dentist_performance(inicio, fin)
        return {"rendimiento_dentistas": performance_data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en rendimiento de dentistas: {str(e)}")


@router.get("/roi/comparativa")
async def get_roi_comparative(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Obtiene comparativa de ROI entre tratamientos y dentistas
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=90)
        
        # ROI por tratamiento
        roi_tratamientos = await calculate_treatment_roi(inicio, fin)
        
        # ROI por dentista
        roi_dentistas = await analyze_dentist_performance(inicio, fin)
        
        # Calcular promedios
        avg_roi_tratamientos = sum(t["roi_porcentaje"] for t in roi_tratamientos) / len(roi_tratamientos) if roi_tratamientos else 0
        avg_roi_dentistas = sum(d["roi_porcentaje"] for d in roi_dentistas) / len(roi_dentistas) if roi_dentistas else 0
        
        return {
            "comparativa": {
                "roi_promedio_tratamientos": round(avg_roi_tratamientos, 2),
                "roi_promedio_dentistas": round(avg_roi_dentistas, 2),
                "mejor_tratamiento": max(roi_tratamientos, key=lambda x: x["roi_porcentaje"]) if roi_tratamientos else None,
                "mejor_dentista": max(roi_dentistas, key=lambda x: x["roi_porcentaje"]) if roi_dentistas else None,
                "tratamientos_detalle": roi_tratamientos[:10],  # Top 10
                "dentistas_detalle": roi_dentistas[:10]
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en comparativa ROI: {str(e)}")


# ==================== PREDICCIONES ML ====================

@router.get("/predicciones/demanda")
async def get_demand_predictions(meses_futuro: int = Query(3, ge=1, le=12)):
    """
    Obtiene predicciones de demanda para los próximos meses
    """
    try:
        predictions = await predict_demand(meses_futuro)
        return {"predicciones": predictions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicciones: {str(e)}")


@router.get("/predicciones/tendencias")
async def get_trend_analysis():
    """
    Obtiene análisis de tendencias históricas
    """
    try:
        # Últimos 12 meses
        fin = datetime.now()
        inicio = fin - timedelta(days=365)
        
        pipeline = [
            {"$match": {"fecha_emision": {"$gte": inicio, "$lte": fin}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$fecha_emision"},
                    "month": {"$month": "$fecha_emision"}
                },
                "ingresos": {"$sum": "$total"},
                "facturas": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        
        tendencias = await db.facturas.aggregate(pipeline).to_list(length=12)
        
        # Calcular tasa de crecimiento
        if len(tendencias) >= 2:
            ingresos_inicial = tendencias[0]["ingresos"]
            ingresos_final = tendencias[-1]["ingresos"]
            crecimiento = ((ingresos_final - ingresos_inicial) / ingresos_inicial * 100) if ingresos_inicial > 0 else 0
        else:
            crecimiento = 0
        
        return {
            "tendencias": [
                {
                    "mes": f"{t['_id']['year']}-{t['_id']['month']:02d}",
                    "ingresos": round(t["ingresos"], 2),
                    "facturas": t["facturas"]
                }
                for t in tendencias
            ],
            "tasa_crecimiento_anual": round(crecimiento, 2)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de tendencias: {str(e)}")


@router.get("/predicciones/alertas")
async def get_predictive_alerts():
    """
    Obtiene alertas basadas en predicciones y análisis
    """
    try:
        alertas = []
        
        # Pacientes en riesgo de abandono
        pacientes = await db.pacientes.find({}).to_list(length=None)
        pacientes_riesgo = []
        
        for paciente in pacientes:
            paciente_id = str(paciente["_id"])
            riesgo = await calculate_churn_risk(paciente_id)
            
            if riesgo > 70:  # Alto riesgo
                pacientes_riesgo.append({
                    "paciente_id": paciente_id,
                    "nombre": paciente.get("nombre", ""),
                    "riesgo": riesgo
                })
        
        if pacientes_riesgo:
            alertas.append({
                "tipo": "churn_risk",
                "severidad": "alta",
                "mensaje": f"{len(pacientes_riesgo)} pacientes en riesgo de abandono",
                "detalles": pacientes_riesgo[:5]  # Top 5
            })
        
        # Verificar caída en conversiones
        fin = datetime.now()
        mes_actual = fin - timedelta(days=30)
        mes_anterior = fin - timedelta(days=60)
        
        funnel_actual = await analyze_conversion_funnel(mes_actual, fin)
        funnel_anterior = await analyze_conversion_funnel(mes_anterior, mes_actual)
        
        tasa_actual = funnel_actual.get("tasa_global", 0)
        tasa_anterior = funnel_anterior.get("tasa_global", 0)
        
        if tasa_anterior > 0:
            cambio = ((tasa_actual - tasa_anterior) / tasa_anterior * 100)
            if cambio < -10:  # Caída >10%
                alertas.append({
                    "tipo": "conversion_drop",
                    "severidad": "media",
                    "mensaje": f"Caída en tasa de conversión del {abs(round(cambio, 2))}%",
                    "detalles": {
                        "tasa_anterior": round(tasa_anterior, 2),
                        "tasa_actual": round(tasa_actual, 2)
                    }
                })
        
        return {"alertas": alertas}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando alertas: {str(e)}")


# ==================== REPORTES ====================

@router.post("/reportes/generar")
async def generate_report(
    tipo: str = Query(..., regex="^(general|pacientes|roi|conversiones)$"),
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    formato: str = Query("json", regex="^(json|pdf)$")
):
    """
    Genera reporte personalizado de analytics
    """
    try:
        if fecha_inicio and fecha_fin:
            inicio = datetime.fromisoformat(fecha_inicio)
            fin = datetime.fromisoformat(fecha_fin)
        else:
            fin = datetime.now()
            inicio = fin - timedelta(days=30)
        
        reporte = {
            "tipo": tipo,
            "periodo": {
                "inicio": inicio.isoformat(),
                "fin": fin.isoformat()
            },
            "generado": datetime.now().isoformat(),
            "datos": {}
        }
        
        if tipo == "general":
            overview = await get_analytics_overview(inicio.isoformat(), fin.isoformat())
            reporte["datos"] = overview
        
        elif tipo == "pacientes":
            segmentos = await analyze_patient_segments()
            ltv_ranking = await get_ltv_ranking(20)
            reporte["datos"] = {
                "segmentacion": segmentos,
                "top_pacientes": ltv_ranking["ranking"]
            }
        
        elif tipo == "roi":
            roi_tratamientos = await calculate_treatment_roi(inicio, fin)
            roi_dentistas = await analyze_dentist_performance(inicio, fin)
            reporte["datos"] = {
                "roi_tratamientos": roi_tratamientos,
                "roi_dentistas": roi_dentistas
            }
        
        elif tipo == "conversiones":
            funnel = await analyze_conversion_funnel(inicio, fin)
            reporte["datos"] = funnel
        
        # TODO: Implementar generación PDF cuando se despliegue
        if formato == "pdf":
            return {
                "mensaje": "Generación PDF requiere despliegue con bibliotecas adicionales",
                "reporte_json": reporte
            }
        
        return reporte
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")


@router.get("/reportes/programados")
async def get_scheduled_reports():
    """
    Obtiene lista de reportes programados
    """
    try:
        # Por ahora retornar vacío - se implementará con sistema de tareas
        return {
            "reportes_programados": [],
            "mensaje": "Sistema de reportes programados pendiente de implementación en despliegue"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo reportes: {str(e)}")


# ==================== MÉTRICAS TIEMPO REAL ====================

@router.get("/metricas/tiempo-real")
async def get_realtime_metrics():
    """
    Obtiene métricas en tiempo real (hoy)
    """
    try:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Citas de hoy
        citas_hoy = await db.citas.count_documents({
            "fecha": {"$gte": hoy}
        })
        
        # Ingresos de hoy
        pipeline_ingresos = [
            {"$match": {
                "fecha_emision": {"$gte": hoy},
                "estado": {"$in": ["emitida", "pagada"]}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]
        ingresos = await db.facturas.aggregate(pipeline_ingresos).to_list(length=1)
        ingresos_hoy = ingresos[0]["total"] if ingresos else 0
        
        # Nuevos pacientes esta semana
        semana_inicio = hoy - timedelta(days=hoy.weekday())
        nuevos_pacientes = await db.pacientes.count_documents({
            "fecha_registro": {"$gte": semana_inicio}
        })
        
        return {
            "fecha": datetime.now().isoformat(),
            "metricas": {
                "citas_hoy": citas_hoy,
                "ingresos_hoy": round(ingresos_hoy, 2),
                "nuevos_pacientes_semana": nuevos_pacientes
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en métricas tiempo real: {str(e)}")
