from .patient import Patient, PatientCreate, PatientUpdate, PatientInDB
from .appointment import Appointment, AppointmentCreate, AppointmentUpdate, AppointmentInDB
from .conversation import Conversation, ConversationCreate, ConversationUpdate, ConversationInDB
from .message import Message, MessageCreate, MessageInDB
from .template import MessageTemplate, MessageTemplateCreate, MessageTemplateUpdate, ConsentTemplate, ConsentTemplateCreate
from .ai_config import AIConfig, AIConfigCreate, AIConfigUpdate, AIResponse

__all__ = [
    "Patient", "PatientCreate", "PatientUpdate", "PatientInDB",
    "Appointment", "AppointmentCreate", "AppointmentUpdate", "AppointmentInDB",
    "Conversation", "ConversationCreate", "ConversationUpdate", "ConversationInDB",
    "Message", "MessageCreate", "MessageInDB",
    "MessageTemplate", "MessageTemplateCreate", "MessageTemplateUpdate",
    "ConsentTemplate", "ConsentTemplateCreate",
    "AIConfig", "AIConfigCreate", "AIConfigUpdate", "AIResponse"
]
