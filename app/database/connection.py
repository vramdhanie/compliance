from pymongo import MongoClient
import os
from typing import Optional, Any, Dict, cast

from app.database.types import MongoCollection, Database


class MongoDB:
    _instance = None
    _client: Optional[Any] = None
    _db: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize if not already initialized
        if MongoDB._client is None:
            self.connect()

    def connect(self, connection_string: Optional[str] = None, db_name: Optional[str] = None):
        """
        Connect to MongoDB using the provided connection string or default to localhost
        
        Args:
            connection_string: MongoDB connection string (default: mongodb://localhost:27017)
            db_name: Database name (default: compliance_db)
        """
        connection_string = connection_string or os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        db_name = db_name or os.environ.get("MONGO_DB", "compliance_db")
        
        try:
            MongoDB._client = MongoClient(connection_string)
            MongoDB._db = cast(Database, MongoDB._client[db_name])
            print(f"Connected to MongoDB: {connection_string}, database: {db_name}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise

    def get_database(self) -> Database | None:
        """Returns the database instance"""
        if MongoDB._db is None:
            self.connect()
        return MongoDB._db

    def get_collection(self, collection_name: str) -> MongoCollection[dict[str, Any]]:
        """
        Get a collection from the database
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            pymongo.collection.Collection: The requested collection
        """
        db = self.get_database()
        if db is None:
            raise ConnectionError("Database connection not established")
        return cast(MongoCollection[Dict[str, Any]], db[collection_name])

    def close(self):
        """Close the MongoDB connection"""
        if MongoDB._client:
            MongoDB._client.close()
            MongoDB._client = None
            MongoDB._db = None
            print("MongoDB connection closed")


# Create a singleton instance to be imported by other modules
db = MongoDB() 