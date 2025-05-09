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
from app.database.qa_storage import QAStorage
from app.database.qa_vector_store import QAVectorStore

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
    "VectorStore",
    "QAStorage",
    "QAVectorStore"
] 