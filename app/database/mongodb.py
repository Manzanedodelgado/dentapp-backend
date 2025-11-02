from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
from typing import Optional


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


mongodb = MongoDB()


async def connect_to_mongo():
    """Conectar a MongoDB"""
    print(f"Conectando a MongoDB en {settings.MONGODB_URL}...")
    mongodb.client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongodb.db = mongodb.client[settings.MONGODB_DB]
    print("MongoDB conectado exitosamente")


async def close_mongo_connection():
    """Cerrar conexión a MongoDB"""
    if mongodb.client:
        mongodb.client.close()
        print("MongoDB desconectado")


def get_database() -> AsyncIOMotorDatabase:
    """Obtener instancia de base de datos"""
    return mongodb.db
