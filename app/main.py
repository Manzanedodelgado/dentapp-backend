from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.routes import (
    patients_router,
    appointments_router,
    conversations_router,
    whatsapp_router,
    templates_router,
    ai_router,
    facturas_router,
    analytics_router,
    communication_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionar ciclo de vida de la aplicación"""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API REST para gestión dental con WhatsApp y agente IA",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(patients_router, prefix="/api")
app.include_router(appointments_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(whatsapp_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(facturas_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(communication_router, prefix="/api")


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Rubio Garcia Dentapp API",
        "version": settings.VERSION,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
