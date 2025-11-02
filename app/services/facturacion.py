"""
Servicios para gestion de facturas VERIFACTU
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.factura import (
    Factura, FacturaCreate, LineaFactura, EmisorData, ReceptorData
)


class FacturacionService:
    """Servicios de logica de negocio para facturacion"""
    
    @staticmethod
    def calcular_linea_factura(
        concepto: str,
        cantidad: float,
        precio_unitario: float,
        tipo_iva: str = "21",
        descuento: float = 0.0
    ) -> LineaFactura:
        """Calcular totales de una linea de factura"""
        
        # Calcular base imponible
        subtotal_linea = cantidad * precio_unitario
        importe_descuento = subtotal_linea * (descuento / 100) if descuento > 0 else 0
        base_imponible = subtotal_linea - importe_descuento
        
        # Calcular IVA
        iva_porcentaje = {
            "21": 0.21,
            "10": 0.10,
            "4": 0.04,
            "0": 0.00,
            "exento": 0.00
        }
        
        cuota_iva = base_imponible * iva_porcentaje.get(tipo_iva, 0.21)
        total_linea = base_imponible + cuota_iva
        
        return LineaFactura(
            concepto=concepto,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            descuento=descuento,
            tipo_iva=tipo_iva,
            base_imponible=round(base_imponible, 2),
            cuota_iva=round(cuota_iva, 2),
            total_linea=round(total_linea, 2)
        )
    
    @staticmethod
    def calcular_totales_factura(lineas: List[LineaFactura]) -> Dict[str, float]:
        """Calcular totales de la factura completa"""
        subtotal = sum(linea.base_imponible for linea in lineas)
        total_iva = sum(linea.cuota_iva for linea in lineas)
        total_factura = sum(linea.total_linea for linea in lineas)
        
        return {
            "subtotal": round(subtotal, 2),
            "total_iva": round(total_iva, 2),
            "total_factura": round(total_factura, 2)
        }
    
    @staticmethod
    def generar_numero_factura(serie: str, anio: int, ultimo_numero: int = 0) -> str:
        """Generar numero de factura correlativo"""
        nuevo_numero = ultimo_numero + 1
        return f"F{anio}-{serie}{nuevo_numero:04d}"
    
    @staticmethod
    def generar_hash_verifactu(factura_data: dict) -> str:
        """Generar hash SHA-256 para verificacion VERIFACTU"""
        # Campos criticos para el hash
        campos_hash = {
            "numero": factura_data.get("numero"),
            "fecha_emision": str(factura_data.get("fecha_emision")),
            "emisor_nif": factura_data.get("emisor", {}).get("nif"),
            "receptor_nombre": factura_data.get("receptor", {}).get("nombre_completo"),
            "total_factura": str(factura_data.get("total_factura"))
        }
        
        # Crear string ordenado y hashear
        hash_string = json.dumps(campos_hash, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    @staticmethod
    def generar_qr_data_verifactu(factura: Factura) -> str:
        """Generar datos para codigo QR VERIFACTU"""
        qr_data = {
            "version": "1.0",
            "tipo_documento": "FC",
            "id_emisor": factura.emisor.nif,
            "fecha_emision": factura.fecha_emision.strftime("%Y-%m-%d"),
            "numero_factura": factura.numero,
            "importe_total": f"{factura.total_factura:.2f}",
            "iva_total": f"{factura.total_iva:.2f}",
            "hash_verificacion": factura.verificacion_hash or "",
            "url_verificacion": f"https://verificacion.rubiogarciadental.com/facturas/{factura.numero}"
        }
        
        return json.dumps(qr_data)
    
    @staticmethod
    def validar_nif_cif(nif: str) -> bool:
        """Validacion basica de NIF/CIF espanol"""
        if not nif or len(nif) != 9:
            return False
        
        # Validacion simple: primer caracter letra o numero, resto numeros excepto ultimo
        primera = nif[0]
        numeros = nif[1:8]
        ultima = nif[8]
        
        # CIF: primera letra, 7 numeros, letra/numero
        # NIF: 8 numeros, letra
        
        if primera.isalpha():  # CIF
            return numeros.isdigit()
        else:  # NIF
            return nif[:8].isdigit() and ultima.isalpha()
    
    @staticmethod
    def calcular_fecha_vencimiento(fecha_emision: datetime, dias_vencimiento: int = 30) -> datetime:
        """Calcular fecha de vencimiento"""
        return fecha_emision + timedelta(days=dias_vencimiento)
    
    @staticmethod
    def crear_factura_desde_tratamientos(
        emisor: EmisorData,
        receptor: ReceptorData,
        tratamientos: List[Dict],
        serie: str = "A",
        forma_pago: str = "transferencia",
        notas: Optional[str] = None,
        appointment_id: Optional[str] = None
    ) -> FacturaCreate:
        """Crear factura automaticamente desde lista de tratamientos"""
        
        # Crear lineas de factura
        lineas = []
        for tratamiento in tratamientos:
            linea = FacturacionService.calcular_linea_factura(
                concepto=tratamiento.get("concepto", "Tratamiento dental"),
                cantidad=tratamiento.get("cantidad", 1),
                precio_unitario=tratamiento.get("precio_unitario", 0),
                tipo_iva=tratamiento.get("tipo_iva", "21"),
                descuento=tratamiento.get("descuento", 0)
            )
            lineas.append(linea)
        
        # Calcular totales
        totales = FacturacionService.calcular_totales_factura(lineas)
        
        # Fecha emision y vencimiento
        fecha_emision = datetime.utcnow()
        fecha_vencimiento = FacturacionService.calcular_fecha_vencimiento(fecha_emision)
        
        # Crear factura (el numero se asignara en el endpoint)
        factura_data = FacturaCreate(
            numero="",  # Se asignara automaticamente
            serie=serie,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            emisor=emisor,
            receptor=receptor,
            lineas=lineas,
            subtotal=totales["subtotal"],
            total_iva=totales["total_iva"],
            total_factura=totales["total_factura"],
            tipo_factura="F1",
            estado="borrador",
            appointment_id=appointment_id,
            notas=notas,
            forma_pago=forma_pago
        )
        
        return factura_data


class DashboardService:
    """Servicios para dashboard financiero"""
    
    @staticmethod
    def calcular_metricas_mensuales(facturas: List[Factura], mes: int, anio: int) -> Dict:
        """Calcular metricas financieras de un mes especifico"""
        facturas_mes = [
            f for f in facturas 
            if f.fecha_emision.month == mes and f.fecha_emision.year == anio
        ]
        
        ingresos_total = sum(
            f.total_factura for f in facturas_mes 
            if f.estado in ["emitida", "pagada"]
        )
        
        facturas_pagadas = [f for f in facturas_mes if f.estado == "pagada"]
        ingresos_cobrados = sum(f.total_factura for f in facturas_pagadas)
        
        return {
            "mes": mes,
            "anio": anio,
            "ingresos_total": round(ingresos_total, 2),
            "ingresos_cobrados": round(ingresos_cobrados, 2),
            "num_facturas": len(facturas_mes),
            "num_facturas_pagadas": len(facturas_pagadas)
        }
    
    @staticmethod
    def calcular_ingresos_por_tratamiento(facturas: List[Factura]) -> List[Dict]:
        """Calcular ingresos agrupados por tipo de tratamiento"""
        tratamientos_ingresos = {}
        
        for factura in facturas:
            if factura.estado in ["emitida", "pagada"]:
                for linea in factura.lineas:
                    concepto = linea.concepto
                    if concepto in tratamientos_ingresos:
                        tratamientos_ingresos[concepto] += linea.total_linea
                    else:
                        tratamientos_ingresos[concepto] = linea.total_linea
        
        # Ordenar por ingresos
        resultado = [
            {"tratamiento": k, "ingresos": round(v, 2)}
            for k, v in sorted(
                tratamientos_ingresos.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        ]
        
        return resultado
    
    @staticmethod
    def calcular_distribucion_estados(facturas: List[Factura]) -> List[Dict]:
        """Calcular distribucion de facturas por estado"""
        estados_count = {}
        
        for factura in facturas:
            estado = factura.estado
            if estado in estados_count:
                estados_count[estado] += 1
            else:
                estados_count[estado] = 1
        
        return [
            {"estado": k, "cantidad": v}
            for k, v in estados_count.items()
        ]
