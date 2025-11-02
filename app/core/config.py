from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "rubio_garcia_dentapp"
    
    # WhatsApp Service
    WHATSAPP_SERVICE_URL: str = "http://localhost:3001"
    
    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    
    # App Config
    DEBUG: bool = True
    APP_NAME: str = "Rubio Garcia Dentapp API"
    VERSION: str = "1.0.0"
    
    # Server Config (Railway compatibility)
    PORT: int = int(os.getenv("PORT", "8000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
