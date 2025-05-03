"""Database module for MongoDB and vector storage integration"""

from app.database.connection import db
from app.database.types import (
    Database,
    MongoCollection,
    InsertOneResult,
    InsertManyResult,
    UpdateResult,
    DeleteResult,
    Cursor
)
from app.database.documents import DocumentStorage
from app.database.vector_store import VectorStore

__all__ = [
    "db",
    "Database",
    "MongoCollection",
    "InsertOneResult",
    "InsertManyResult",
    "UpdateResult",
    "DeleteResult",
    "Cursor",
    "DocumentStorage",
    "VectorStore"
] 