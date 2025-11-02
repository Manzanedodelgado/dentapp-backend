"""
Servicio de Email (SMTP) para Sistema de Comunicación
Rubio Garcia Dentapp
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from typing import List, Dict, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para envío de emails vía SMTP"""
    
    def __init__(self, smtp_config: Dict):
        """
        Inicializar servicio de email
        
        Args:
            smtp_config: Configuración SMTP
                - server: Servidor SMTP
                - port: Puerto
                - username: Usuario
                - password: Contraseña
                - use_tls: Usar TLS
                - from_name: Nombre remitente
                - from_email: Email remitente
        """
        self.smtp_server = smtp_config["server"]
        self.smtp_port = smtp_config["port"]
        self.username = smtp_config["username"]
        self.password = smtp_config["password"]
        self.use_tls = smtp_config.get("use_tls", True)
        self.from_name = smtp_config.get("from_name", "Rubio Garcia")
        self.from_email = smtp_config["from_email"]
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        template_data: Optional[Dict] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Enviar email con template HTML
        
        Args:
            to: Lista de destinatarios
            subject: Asunto del email
            html_content: Contenido HTML
            text_content: Contenido texto plano (fallback)
            template_data: Datos para reemplazar en template
            cc: Lista de copia
            bcc: Lista de copia oculta
            attachments: Lista de archivos adjuntos
        
        Returns:
            Dict con resultado del envío
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = ', '.join(to)
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Generar Message-ID único
            message_id = self._generate_message_id()
            msg['Message-ID'] = message_id
            
            # Procesar templates con variables
            processed_html = self.process_template(html_content, template_data or {})
            processed_text = self.process_template(
                text_content or self._html_to_text(html_content),
                template_data or {}
            )
            
            # Adjuntar contenido
            text_part = MIMEText(processed_text, 'plain', 'utf-8')
            html_part = MIMEText(processed_html, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Adjuntar archivos si los hay
            if attachments:
                for attachment in attachments:
                    self._attach_file(msg, attachment)
            
            # Enviar email
            all_recipients = to + (cc or []) + (bcc or [])
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.set_debuglevel(0)
                
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                server.send_message(msg, self.from_email, all_recipients)
            
            logger.info(f"Email enviado exitosamente a {len(all_recipients)} destinatarios")
            
            return {
                "success": True,
                "message_id": message_id,
                "recipients": len(all_recipients),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Error de autenticación SMTP: {str(e)}")
            return {
                "success": False,
                "error": "Credenciales SMTP inválidas",
                "details": str(e)
            }
        
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Destinatarios rechazados: {str(e)}")
            return {
                "success": False,
                "error": "Uno o más destinatarios fueron rechazados",
                "details": str(e)
            }
        
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP: {str(e)}")
            return {
                "success": False,
                "error": "Error al enviar email",
                "details": str(e)
            }
        
        except Exception as e:
            logger.error(f"Error inesperado al enviar email: {str(e)}")
            return {
                "success": False,
                "error": "Error inesperado",
                "details": str(e)
            }
    
    def process_template(self, template: str, data: Dict) -> str:
        """
        Procesar template reemplazando variables
        
        Variables soportadas:
        - {{ patient_name }}
        - {{ appointment_date }}
        - {{ appointment_time }}
        - {{ dentist_name }}
        - {{ clinic_name }}
        - {{ clinic_phone }}
        - {{ clinic_address }}
        - etc.
        
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
    
    def _html_to_text(self, html: str) -> str:
        """
        Convertir HTML a texto plano simple
        
        Args:
            html: Contenido HTML
        
        Returns:
            Texto plano
        """
        # Remover tags HTML básicos
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decodificar entidades HTML comunes
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Limpiar espacios múltiples
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _generate_message_id(self) -> str:
        """
        Generar Message-ID único
        
        Returns:
            Message-ID en formato RFC 2822
        """
        import uuid
        domain = self.from_email.split('@')[1] if '@' in self.from_email else 'localhost'
        return f"<{uuid.uuid4()}@{domain}>"
    
    def _attach_file(self, msg: MIMEMultipart, attachment: Dict):
        """
        Adjuntar archivo al mensaje
        
        Args:
            msg: Mensaje MIME
            attachment: Dict con 'filename', 'content', 'mimetype'
        """
        from email.mime.base import MIMEBase
        from email import encoders
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment['content'])
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {attachment["filename"]}'
        )
        msg.attach(part)
    
    def validate_email(self, email: str) -> bool:
        """
        Validar formato de email
        
        Args:
            email: Email a validar
        
        Returns:
            True si es válido
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def test_connection(self) -> Dict:
        """
        Probar conexión SMTP
        
        Returns:
            Dict con resultado de la prueba
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.set_debuglevel(0)
                
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
            
            return {
                "success": True,
                "message": "Conexión SMTP exitosa"
            }
        
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "error": "Credenciales inválidas"
            }
        
        except smtplib.SMTPConnectError:
            return {
                "success": False,
                "error": "No se pudo conectar al servidor SMTP"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_delivery_status(self, message_id: str) -> Dict:
        """
        Obtener estado de entrega (básico)
        
        Nota: Esto requiere implementación con webhooks o APIs específicas
        del proveedor de email (SendGrid, Mailgun, etc.)
        
        Args:
            message_id: ID del mensaje
        
        Returns:
            Dict con estado estimado
        """
        # Implementación básica - en producción usar webhooks
        return {
            "message_id": message_id,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Estado real requiere webhooks del proveedor"
        }
