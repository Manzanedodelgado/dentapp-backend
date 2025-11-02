from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, date
from bson import ObjectId
from app.models.patient import PyObjectId


class EmisorData(BaseModel):
    """Datos del emisor de la factura (clinica dental)"""
    nif: str = Field(..., description="NIF/CIF de la clinica")
    razon_social: str = Field(..., description="Razon social de la clinica")
    direccion: str = Field(..., description="Direccion completa")
    municipio: str = Field(..., description="Municipio")
    codigo_postal: str = Field(..., pattern=r"^\d{5}$", description="Codigo postal (5 digitos)")
    provincia: str = Field(..., description="Provincia")
    registro_mercantil: Optional[str] = Field(None, description="Registro mercantil si aplica")
    email: str = Field(..., description="Email de contacto")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nif": "B12345678",
                "razon_social": "Clinica Dental Rubio Garcia SL",
                "direccion": "Calle Mayor 123",
                "municipio": "Madrid",
                "codigo_postal": "28001",
                "provincia": "Madrid",
                "email": "facturacion@rubiogarciadental.com"
            }
        }


class ReceptorData(BaseModel):
    """Datos del receptor de la factura (paciente)"""
    nif: Optional[str] = Field(None, description="NIF del paciente (opcional)")
    nombre_completo: str = Field(..., description="Nombre completo del paciente")
    direccion: Optional[str] = Field(None, description="Direccion del paciente")
    email: str = Field(..., description="Email del paciente")
    telefono: Optional[str] = Field(None, description="Telefono del paciente")


class LineaFactura(BaseModel):
    """Linea individual de la factura"""
    concepto: str = Field(..., description="Descripcion del tratamiento/servicio")
    cantidad: float = Field(default=1.0, ge=0, description="Cantidad de unidades")
    precio_unitario: float = Field(..., ge=0, description="Precio por unidad (sin IVA)")
    descuento: Optional[float] = Field(default=0.0, ge=0, le=100, description="Descuento en porcentaje")
    tipo_iva: Literal["21", "10", "4", "0", "exento"] = Field(default="21", description="Tipo de IVA aplicable")
    base_imponible: float = Field(..., ge=0, description="Base imponible (cantidad * precio - descuento)")
    cuota_iva: float = Field(..., ge=0, description="Cuota de IVA calculada")
    total_linea: float = Field(..., ge=0, description="Total de la linea (base + IVA)")


class FacturaBase(BaseModel):
    """Modelo base de factura VERIFACTU"""
    numero: str = Field(..., description="Numero de factura (ej: F2025-001)")
    serie: str = Field(default="A", description="Serie de la factura (A, B, C)")
    fecha_emision: datetime = Field(default_factory=datetime.utcnow, description="Fecha de emision")
    fecha_vencimiento: datetime = Field(..., description="Fecha de vencimiento")
    
    # Datos emisor y receptor
    emisor: EmisorData
    receptor: ReceptorData
    
    # Lineas de factura
    lineas: List[LineaFactura] = Field(..., min_length=1, description="Lineas de la factura")
    
    # Totales
    subtotal: float = Field(..., ge=0, description="Subtotal sin IVA")
    total_iva: float = Field(..., ge=0, description="Total IVA")
    total_factura: float = Field(..., ge=0, description="Total factura (subtotal + IVA)")
    
    # VERIFACTU especifico
    tipo_factura: Literal["F1", "F2", "F3", "F4", "R1", "R2", "R3", "R4", "R5"] = Field(
        default="F1",
        description="F1: Factura normal, F2: Simplificada, R1-R5: Rectificativas"
    )
    factoring: bool = Field(default=False, description="Operacion de factoring")
    bienes_usados: bool = Field(default=False, description="Regimen de bienes usados")
    regimen_especial: Optional[str] = Field(
        default="ninguno",
        description="Regimen especial aplicable"
    )
    
    # Estado y seguimiento
    estado: Literal["borrador", "emitida", "anulada", "pagada"] = Field(
        default="borrador",
        description="Estado actual de la factura"
    )
    fecha_envio_hacienda: Optional[datetime] = Field(None, description="Fecha envio a Hacienda")
    respuesta_hacienda: Optional[str] = Field(None, description="Respuesta de Hacienda")
    
    # QR VERIFACTU
    qr_data: Optional[str] = Field(None, description="Datos del codigo QR VERIFACTU")
    verificacion_hash: Optional[str] = Field(None, description="Hash SHA-256 para verificacion")
    
    # Vinculacion con cita (opcional)
    appointment_id: Optional[str] = Field(None, description="ID de la cita asociada")
    
    # Notas adicionales
    notas: Optional[str] = Field(None, description="Notas o comentarios adicionales")
    forma_pago: Optional[str] = Field(
        default="transferencia",
        description="Metodo de pago: transferencia, tarjeta, bizum, efectivo"
    )


class FacturaCreate(FacturaBase):
    """Modelo para crear nueva factura"""
    pass


class FacturaUpdate(BaseModel):
    """Modelo para actualizar factura existente"""
    numero: Optional[str] = None
    serie: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    emisor: Optional[EmisorData] = None
    receptor: Optional[ReceptorData] = None
    lineas: Optional[List[LineaFactura]] = None
    subtotal: Optional[float] = None
    total_iva: Optional[float] = None
    total_factura: Optional[float] = None
    tipo_factura: Optional[str] = None
    estado: Optional[str] = None
    notas: Optional[str] = None
    forma_pago: Optional[str] = None


class FacturaInDB(FacturaBase):
    """Modelo de factura en base de datos"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="ID del usuario que creo la factura")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "numero": "F2025-001",
                "serie": "A",
                "fecha_emision": "2025-11-01T10:00:00",
                "fecha_vencimiento": "2025-11-30T23:59:59",
                "emisor": {
                    "nif": "B12345678",
                    "razon_social": "Clinica Dental Rubio Garcia SL",
                    "direccion": "Calle Mayor 123",
                    "municipio": "Madrid",
                    "codigo_postal": "28001",
                    "provincia": "Madrid",
                    "email": "facturacion@rubiogarciadental.com"
                },
                "receptor": {
                    "nombre_completo": "Maria Garcia Lopez",
                    "email": "maria@example.com",
                    "telefono": "664123456"
                },
                "lineas": [
                    {
                        "concepto": "Limpieza dental profesional",
                        "cantidad": 1,
                        "precio_unitario": 60.00,
                        "descuento": 0,
                        "tipo_iva": "21",
                        "base_imponible": 60.00,
                        "cuota_iva": 12.60,
                        "total_linea": 72.60
                    }
                ],
                "subtotal": 60.00,
                "total_iva": 12.60,
                "total_factura": 72.60,
                "tipo_factura": "F1",
                "estado": "emitida"
            }
        }


class Factura(FacturaInDB):
    """Modelo completo de factura para respuestas API"""
    pass


class DashboardFinanciero(BaseModel):
    """Metricas del dashboard financiero"""
    ingresos_mes_actual: float = Field(..., description="Ingresos del mes en curso")
    ingresos_mes_anterior: float = Field(..., description="Ingresos del mes anterior")
    ingresos_anio_actual: float = Field(..., description="Ingresos del anio en curso")
    
    total_facturas: int = Field(..., description="Total de facturas emitidas")
    facturas_pendientes: int = Field(..., description="Facturas pendientes de pago")
    facturas_pagadas: int = Field(..., description="Facturas pagadas")
    facturas_anuladas: int = Field(..., description="Facturas anuladas")
    
    importe_pendiente: float = Field(..., description="Importe total pendiente de cobro")
    importe_cobrado_mes: float = Field(..., description="Importe cobrado este mes")
    
    tratamiento_mas_facturado: Optional[str] = Field(None, description="Tratamiento que mas ingresos genera")
    valor_medio_factura: float = Field(..., description="Valor medio de factura")
    
    # Datos para graficos
    ingresos_por_mes: List[dict] = Field(default_factory=list, description="Ingresos mensuales ultimos 12 meses")
    ingresos_por_tratamiento: List[dict] = Field(default_factory=list, description="Ingresos por tipo de tratamiento")
    facturas_por_estado: List[dict] = Field(default_factory=list, description="Distribucion de facturas por estado")


class FacturaAutogeneradaRequest(BaseModel):
    """Request para generar factura automaticamente desde una cita"""
    appointment_id: str = Field(..., description="ID de la cita")
    tratamientos: List[dict] = Field(..., description="Lista de tratamientos realizados")
    forma_pago: str = Field(default="transferencia", description="Forma de pago")
    notas: Optional[str] = Field(None, description="Notas adicionales")
