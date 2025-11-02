"""
Servicio de SMS (Twilio) para Sistema de Comunicación
Rubio Garcia Dentapp
"""

from typing import List, Dict, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

# Nota: En producción, descomentar y usar Twilio real
# from twilio.rest import Client
# from twilio.base.exceptions import TwilioException


class SMSService:
    """Servicio para envío de SMS vía Twilio"""
    
    def __init__(self, twilio_config: Dict):
        """
        Inicializar servicio de SMS
        
        Args:
            twilio_config: Configuración de Twilio
                - account_sid: Account SID
                - auth_token: Auth Token
                - from_number: Número de teléfono Twilio
        """
        self.account_sid = twilio_config["account_sid"]
        self.auth_token = twilio_config["auth_token"]
        self.from_number = twilio_config["from_number"]
        
        # En producción, descomentar:
        # self.client = Client(self.account_sid, self.auth_token)
        
        # Modo desarrollo (simular):
        self.client = None
        self.dev_mode = True
        
        logger.info(f"SMSService initialized (dev_mode: {self.dev_mode})")
    
    def send_sms(
        self,
        to: List[str],
        message: str,
        template_data: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Enviar SMS a lista de destinatarios
        
        Args:
            to: Lista de números de teléfono
            message: Mensaje a enviar
            template_data: Datos para reemplazar en template
        
        Returns:
            Lista de resultados por destinatario
        """
        results = []
        
        # Procesar template
        processed_message = self.process_template(message, template_data or {})
        
        # Validar longitud del mensaje
        if len(processed_message) > 1600:
            logger.warning(f"Mensaje SMS muy largo ({len(processed_message)} chars), se fragmentará")
        
        for phone in to:
            try:
                # Formatear número español
                formatted_phone = self.format_spanish_number(phone)
                
                # Validar número
                if not self.validate_phone(formatted_phone):
                    results.append({
                        "phone": phone,
                        "success": False,
                        "error": "Formato de número inválido"
                    })
                    continue
                
                # Enviar SMS
                if self.dev_mode:
                    # Modo desarrollo: simular envío
                    result = self._send_sms_dev(formatted_phone, processed_message)
                else:
                    # Modo producción: envío real con Twilio
                    result = self._send_sms_twilio(formatted_phone, processed_message)
                
                results.append({
                    "phone": phone,
                    **result
                })
            
            except Exception as e:
                logger.error(f"Error enviando SMS a {phone}: {str(e)}")
                results.append({
                    "phone": phone,
                    "success": False,
                    "error": str(e)
                })
        
        # Estadísticas
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"SMS enviados: {success_count}/{len(results)}")
        
        return results
    
    def _send_sms_dev(self, phone: str, message: str) -> Dict:
        """
        Simular envío de SMS (modo desarrollo)
        
        Args:
            phone: Número de teléfono
            message: Mensaje
        
        Returns:
            Resultado simulado
        """
        import uuid
        
        logger.info(f"[DEV] SMS a {phone}: {message[:50]}...")
        
        return {
            "success": True,
            "message_id": f"SM{uuid.uuid4().hex[:32]}",
            "status": "sent",
            "segments": self._calculate_segments(message),
            "timestamp": datetime.utcnow().isoformat(),
            "dev_mode": True
        }
    
    def _send_sms_twilio(self, phone: str, message: str) -> Dict:
        """
        Enviar SMS vía Twilio (producción)
        
        Args:
            phone: Número de teléfono
            message: Mensaje
        
        Returns:
            Resultado del envío
        """
        # En producción, descomentar:
        """
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone
            )
            
            return {
                "success": True,
                "message_id": message_obj.sid,
                "status": message_obj.status,
                "segments": message_obj.num_segments,
                "price": message_obj.price,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except TwilioException as e:
            logger.error(f"Twilio error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.code if hasattr(e, 'code') else None
            }
        """
        
        # Placeholder para desarrollo
        raise NotImplementedError("Twilio client not configured (dev mode)")
    
    def process_template(self, template: str, data: Dict) -> str:
        """
        Procesar template SMS reemplazando variables
        
        Args:
            template: String del template
            data: Diccionario con variables
        
        Returns:
            Template procesado
        """
        processed = template
        
        for key, value in data.items():
            # Reemplazar variables con formato {{ variable }}
            pattern = r'\{\{\s*' + key + r'\s*\}\}'
            processed = re.sub(pattern, str(value), processed)
        
        return processed
    
    def format_spanish_number(self, phone: str) -> str:
        """
        Formatear número de teléfono español a formato internacional
        
        Args:
            phone: Número de teléfono (varios formatos)
        
        Returns:
            Número en formato +34XXXXXXXXX
        """
        # Remover espacios, guiones, paréntesis
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Remover prefijos comunes
        clean_phone = clean_phone.replace('+', '')
        clean_phone = clean_phone.replace('00', '')
        
        # Formatear según longitud
        if len(clean_phone) == 9:
            # Número español sin prefijo
            return f"+34{clean_phone}"
        elif len(clean_phone) == 11 and clean_phone.startswith('34'):
            # Número con prefijo sin +
            return f"+{clean_phone}"
        elif len(clean_phone) == 12 and clean_phone.startswith('+34'):
            # Ya está bien formateado
            return clean_phone
        else:
            # Retornar sin cambios si no se puede formatear
            return phone
    
    def validate_phone(self, phone: str) -> bool:
        """
        Validar formato de número de teléfono español
        
        Args:
            phone: Número a validar
        
        Returns:
            True si es válido
        """
        # Formato: +34XXXXXXXXX (9 dígitos después del prefijo)
        pattern = r'^\+34[6-9]\d{8}$'
        return bool(re.match(pattern, phone))
    
    def _calculate_segments(self, message: str) -> int:
        """
        Calcular número de segmentos SMS (160 chars por segmento)
        
        Args:
            message: Mensaje
        
        Returns:
            Número de segmentos
        """
        # SMS estándar: 160 chars
        # SMS con caracteres especiales: 70 chars
        # SMS concatenados: 153 chars por segmento (deja espacio para header)
        
        has_special = any(ord(c) > 127 for c in message)
        
        if has_special:
            char_limit = 70
            concat_limit = 67
        else:
            char_limit = 160
            concat_limit = 153
        
        msg_len = len(message)
        
        if msg_len <= char_limit:
            return 1
        else:
            return (msg_len + concat_limit - 1) // concat_limit
    
    def estimate_cost(self, phone: str, message: str) -> Dict:
        """
        Estimar costo de envío de SMS
        
        Args:
            phone: Número de teléfono
            message: Mensaje
        
        Returns:
            Diccionario con estimación de costo
        """
        segments = self._calculate_segments(message)
        
        # Precios aproximados Twilio España (actualizar según tarifa real)
        price_per_segment = 0.06  # EUR
        
        total_price = segments * price_per_segment
        
        return {
            "phone": phone,
            "segments": segments,
            "price_per_segment": price_per_segment,
            "total_price": round(total_price, 2),
            "currency": "EUR",
            "message_length": len(message)
        }
    
    def get_delivery_status(self, message_id: str) -> Dict:
        """
        Obtener estado de entrega de SMS
        
        Args:
            message_id: ID del mensaje
        
        Returns:
            Estado del mensaje
        """
        if self.dev_mode:
            return {
                "message_id": message_id,
                "status": "delivered",
                "timestamp": datetime.utcnow().isoformat(),
                "dev_mode": True
            }
        
        # En producción, descomentar:
        """
        try:
            message = self.client.messages(message_id).fetch()
            
            return {
                "message_id": message_id,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "price": message.price,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except TwilioException as e:
            return {
                "message_id": message_id,
                "error": str(e)
            }
        """
        
        raise NotImplementedError("Twilio client not configured (dev mode)")
    
    def test_connection(self) -> Dict:
        """
        Probar conexión con Twilio
        
        Returns:
            Resultado de la prueba
        """
        if self.dev_mode:
            return {
                "success": True,
                "message": "Modo desarrollo activo",
                "dev_mode": True
            }
        
        # En producción, descomentar:
        """
        try:
            account = self.client.api.accounts(self.account_sid).fetch()
            
            return {
                "success": True,
                "account_name": account.friendly_name,
                "status": account.status,
                "message": "Conexión Twilio exitosa"
            }
        
        except TwilioException as e:
            return {
                "success": False,
                "error": str(e)
            }
        """
        
        return {
            "success": False,
            "error": "Twilio client not configured"
        }
    
    def send_bulk_sms(
        self,
        recipients: List[Dict],
        message_template: str
    ) -> Dict:
        """
        Enviar SMS masivos con personalización
        
        Args:
            recipients: Lista de dict con 'phone' y datos para template
            message_template: Template del mensaje
        
        Returns:
            Resumen de envíos
        """
        results = []
        
        for recipient in recipients:
            phone = recipient.get('phone')
            template_data = {k: v for k, v in recipient.items() if k != 'phone'}
            
            result = self.send_sms([phone], message_template, template_data)
            results.extend(result)
        
        # Calcular estadísticas
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        failed = total - success
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round((success / total * 100) if total > 0 else 0, 2),
            "results": results
        }
