from .patients import router as patients_router
from .appointments import router as appointments_router
from .conversations import router as conversations_router
from .whatsapp import router as whatsapp_router
from .templates import router as templates_router
from .ai import router as ai_router
from .facturas import router as facturas_router
from .analytics import router as analytics_router
from .communication import router as communication_router

__all__ = [
    "patients_router",
    "appointments_router",
    "conversations_router",
    "whatsapp_router",
    "templates_router",
    "ai_router",
    "facturas_router",
    "analytics_router",
    "communication_router"
]
