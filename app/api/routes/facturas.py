"""
Endpoints API para gestion de facturas VERIFACTU
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from app.models.factura import (
    Factura, FacturaCreate, FacturaUpdate, DashboardFinanciero,
    FacturaAutogeneradaRequest, EmisorData, ReceptorData
)
from app.services.facturacion import FacturacionService, DashboardService
from app.database.mongodb import get_database


router = APIRouter(prefix="/facturas", tags=["Facturas VERIFACTU"])


# Datos del emisor por defecto (Clinica Dental Rubio Garcia)
EMISOR_DEFAULT = EmisorData(
    nif="B12345678",
    razon_social="Clinica Dental Rubio Garcia SL",
    direccion="Calle Mayor 123",
    municipio="Madrid",
    codigo_postal="28001",
    provincia="Madrid",
    email="facturacion@rubiogarciadental.com"
)


@router.post("/", response_model=Factura, status_code=status.HTTP_201_CREATED)
async def crear_factura(factura: FacturaCreate):
    """Crear nueva factura VERIFACTU"""
    try:
        db = get_database()
        
        # Generar numero de factura si no existe
        if not factura.numero or factura.numero == "":
            # Obtener ultimo numero de la serie
            anio_actual = datetime.utcnow().year
            ultima_factura = await db.facturas.find_one(
                {"serie": factura.serie, "numero": {"$regex": f"^F{anio_actual}"}},
                sort=[("numero", -1)]
            )
            
            ultimo_numero = 0
            if ultima_factura:
                # Extraer numero de la factura (ej: F2025-A0001 -> 1)
                try:
                    num_parte = ultima_factura["numero"].split("-")[1]
                    ultimo_numero = int(num_parte[1:])  # Quitar la letra de serie
                except:
                    ultimo_numero = 0
            
            factura.numero = FacturacionService.generar_numero_factura(
                factura.serie, anio_actual, ultimo_numero
            )
        
        # Generar hash de verificacion
        factura_dict = factura.model_dump()
        verificacion_hash = FacturacionService.generar_hash_verifactu(factura_dict)
        factura_dict["verificacion_hash"] = verificacion_hash
        
        # Generar datos QR (se generara el QR real en frontend)
        factura_temp = Factura(**factura_dict, id=ObjectId(), created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        qr_data = FacturacionService.generar_qr_data_verifactu(factura_temp)
        factura_dict["qr_data"] = qr_data
        
        # Insertar en base de datos
        factura_dict["created_at"] = datetime.utcnow()
        factura_dict["updated_at"] = datetime.utcnow()
        
        resultado = await db.facturas.insert_one(factura_dict)
        
        # Recuperar factura creada
        factura_creada = await db.facturas.find_one({"_id": resultado.inserted_id})
        
        return Factura(**factura_creada)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear factura: {str(e)}"
        )


@router.get("/", response_model=List[Factura])
async def listar_facturas(
    skip: int = Query(0, ge=0, description="Numero de registros a omitir"),
    limit: int = Query(100, ge=1, le=500, description="Numero maximo de registros"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    serie: Optional[str] = Query(None, description="Filtrar por serie"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)")
):
    """Listar facturas con filtros opcionales"""
    try:
        db = get_database()
        
        # Construir query
        query = {}
        
        if estado:
            query["estado"] = estado
        
        if serie:
            query["serie"] = serie
        
        if fecha_desde or fecha_hasta:
            query["fecha_emision"] = {}
            if fecha_desde:
                query["fecha_emision"]["$gte"] = datetime.fromisoformat(fecha_desde)
            if fecha_hasta:
                query["fecha_emision"]["$lte"] = datetime.fromisoformat(fecha_hasta)
        
        # Obtener facturas
        cursor = db.facturas.find(query).sort("fecha_emision", -1).skip(skip).limit(limit)
        facturas = await cursor.to_list(length=limit)
        
        return [Factura(**factura) for factura in facturas]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar facturas: {str(e)}"
        )


@router.get("/{factura_id}", response_model=Factura)
async def obtener_factura(factura_id: str):
    """Obtener factura por ID"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        factura = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        return Factura(**factura)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener factura: {str(e)}"
        )


@router.put("/{factura_id}", response_model=Factura)
async def actualizar_factura(factura_id: str, factura_update: FacturaUpdate):
    """Actualizar factura existente"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        # Verificar que existe
        factura_existente = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        if not factura_existente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        # No permitir editar facturas emitidas o pagadas
        if factura_existente.get("estado") in ["emitida", "pagada"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden editar facturas emitidas o pagadas"
            )
        
        # Actualizar campos
        update_data = {k: v for k, v in factura_update.model_dump(exclude_unset=True).items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        await db.facturas.update_one(
            {"_id": ObjectId(factura_id)},
            {"$set": update_data}
        )
        
        # Recuperar factura actualizada
        factura_actualizada = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        
        return Factura(**factura_actualizada)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar factura: {str(e)}"
        )


@router.delete("/{factura_id}")
async def anular_factura(factura_id: str):
    """Anular factura (no se elimina, solo se marca como anulada)"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        # Verificar que existe
        factura = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        # Anular factura
        await db.facturas.update_one(
            {"_id": ObjectId(factura_id)},
            {"$set": {"estado": "anulada", "updated_at": datetime.utcnow()}}
        )
        
        return {"message": "Factura anulada correctamente", "factura_id": factura_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al anular factura: {str(e)}"
        )


@router.get("/{factura_id}/qr")
async def obtener_qr_factura(factura_id: str):
    """Obtener datos del codigo QR VERIFACTU para una factura"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        factura = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        return {
            "factura_id": factura_id,
            "numero": factura.get("numero"),
            "qr_data": factura.get("qr_data"),
            "verificacion_hash": factura.get("verificacion_hash")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener QR: {str(e)}"
        )


@router.post("/{factura_id}/enviar")
async def enviar_factura_hacienda(factura_id: str):
    """Enviar factura a Hacienda (simulado para MVP)"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        factura = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        # Actualizar estado (en produccion real se haria integracion con Hacienda)
        await db.facturas.update_one(
            {"_id": ObjectId(factura_id)},
            {
                "$set": {
                    "estado": "emitida",
                    "fecha_envio_hacienda": datetime.utcnow(),
                    "respuesta_hacienda": "Aceptada (simulado)",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": "Factura enviada a Hacienda correctamente",
            "factura_id": factura_id,
            "estado": "emitida"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar factura: {str(e)}"
        )


@router.get("/dashboard/financiero", response_model=DashboardFinanciero)
async def obtener_dashboard_financiero():
    """Obtener metricas del dashboard financiero"""
    try:
        db = get_database()
        
        # Obtener todas las facturas
        facturas_cursor = db.facturas.find({})
        facturas_list = await facturas_cursor.to_list(length=None)
        facturas = [Factura(**f) for f in facturas_list]
        
        # Fecha actual
        ahora = datetime.utcnow()
        mes_actual = ahora.month
        anio_actual = ahora.year
        
        # Mes anterior
        if mes_actual == 1:
            mes_anterior = 12
            anio_anterior = anio_actual - 1
        else:
            mes_anterior = mes_actual - 1
            anio_anterior = anio_actual
        
        # Calcular ingresos mes actual
        metricas_mes_actual = DashboardService.calcular_metricas_mensuales(
            facturas, mes_actual, anio_actual
        )
        ingresos_mes_actual = metricas_mes_actual["ingresos_total"]
        
        # Calcular ingresos mes anterior
        metricas_mes_anterior = DashboardService.calcular_metricas_mensuales(
            facturas, mes_anterior, anio_anterior
        )
        ingresos_mes_anterior = metricas_mes_anterior["ingresos_total"]
        
        # Ingresos año actual
        facturas_anio = [f for f in facturas if f.fecha_emision.year == anio_actual]
        ingresos_anio_actual = sum(
            f.total_factura for f in facturas_anio 
            if f.estado in ["emitida", "pagada"]
        )
        
        # Contadores por estado
        total_facturas = len(facturas)
        facturas_pendientes = len([f for f in facturas if f.estado == "emitida"])
        facturas_pagadas = len([f for f in facturas if f.estado == "pagada"])
        facturas_anuladas = len([f for f in facturas if f.estado == "anulada"])
        
        # Importes
        importe_pendiente = sum(
            f.total_factura for f in facturas if f.estado == "emitida"
        )
        importe_cobrado_mes = sum(
            f.total_factura for f in facturas 
            if f.estado == "pagada" and f.fecha_emision.month == mes_actual
        )
        
        # Ingresos por tratamiento
        ingresos_por_tratamiento = DashboardService.calcular_ingresos_por_tratamiento(facturas)
        tratamiento_mas_facturado = ingresos_por_tratamiento[0]["tratamiento"] if ingresos_por_tratamiento else None
        
        # Valor medio
        facturas_validas = [f for f in facturas if f.estado in ["emitida", "pagada"]]
        valor_medio_factura = (
            sum(f.total_factura for f in facturas_validas) / len(facturas_validas)
            if facturas_validas else 0
        )
        
        # Ingresos por mes (ultimos 12 meses)
        ingresos_por_mes = []
        for i in range(12):
            mes = mes_actual - i
            anio = anio_actual
            if mes <= 0:
                mes += 12
                anio -= 1
            
            metricas = DashboardService.calcular_metricas_mensuales(facturas, mes, anio)
            ingresos_por_mes.insert(0, {
                "mes": f"{anio}-{mes:02d}",
                "ingresos": metricas["ingresos_total"]
            })
        
        # Distribucion por estado
        facturas_por_estado = DashboardService.calcular_distribucion_estados(facturas)
        
        return DashboardFinanciero(
            ingresos_mes_actual=round(ingresos_mes_actual, 2),
            ingresos_mes_anterior=round(ingresos_mes_anterior, 2),
            ingresos_anio_actual=round(ingresos_anio_actual, 2),
            total_facturas=total_facturas,
            facturas_pendientes=facturas_pendientes,
            facturas_pagadas=facturas_pagadas,
            facturas_anuladas=facturas_anuladas,
            importe_pendiente=round(importe_pendiente, 2),
            importe_cobrado_mes=round(importe_cobrado_mes, 2),
            tratamiento_mas_facturado=tratamiento_mas_facturado,
            valor_medio_factura=round(valor_medio_factura, 2),
            ingresos_por_mes=ingresos_por_mes,
            ingresos_por_tratamiento=ingresos_por_tratamiento[:10],  # Top 10
            facturas_por_estado=facturas_por_estado
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener dashboard: {str(e)}"
        )


@router.post("/autogenerar", response_model=Factura)
async def autogenerar_factura_desde_cita(request: FacturaAutogeneradaRequest):
    """Generar factura automaticamente desde una cita completada"""
    try:
        db = get_database()
        
        # Verificar que la cita existe
        if not ObjectId.is_valid(request.appointment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de cita invalido"
            )
        
        cita = await db.appointments.find_one({"_id": ObjectId(request.appointment_id)})
        if not cita:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cita no encontrada"
            )
        
        # Obtener datos del paciente
        paciente = await db.patients.find_one({"_id": ObjectId(cita["patient_id"])})
        if not paciente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado"
            )
        
        # Crear receptor desde datos del paciente
        receptor = ReceptorData(
            nombre_completo=paciente["name"],
            email=paciente.get("email", "sin-email@example.com"),
            telefono=paciente.get("phone")
        )
        
        # Crear factura desde tratamientos
        factura_create = FacturacionService.crear_factura_desde_tratamientos(
            emisor=EMISOR_DEFAULT,
            receptor=receptor,
            tratamientos=request.tratamientos,
            serie="A",
            forma_pago=request.forma_pago,
            notas=request.notas,
            appointment_id=request.appointment_id
        )
        
        # Crear la factura usando el endpoint de creacion
        return await crear_factura(factura_create)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al autogenerar factura: {str(e)}"
        )


@router.post("/{factura_id}/pago")
async def procesar_pago_factura(factura_id: str, metodo_pago: str = "transferencia"):
    """Marcar factura como pagada"""
    try:
        db = get_database()
        
        if not ObjectId.is_valid(factura_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de factura invalido"
            )
        
        factura = await db.facturas.find_one({"_id": ObjectId(factura_id)})
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada"
            )
        
        # Actualizar estado a pagada
        await db.facturas.update_one(
            {"_id": ObjectId(factura_id)},
            {
                "$set": {
                    "estado": "pagada",
                    "forma_pago": metodo_pago,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": "Pago procesado correctamente",
            "factura_id": factura_id,
            "metodo_pago": metodo_pago,
            "estado": "pagada"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar pago: {str(e)}"
        )
