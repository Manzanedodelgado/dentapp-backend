"""
Database package - MongoDB connection
"""

from .mongodb import mongodb, connect_to_mongo, close_mongo_connection, get_database

# Crear alias 'db' para compatibilidad con el código existente
db = mongodb.db

__all__ = [
    "mongodb",
    "db",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database"
]
