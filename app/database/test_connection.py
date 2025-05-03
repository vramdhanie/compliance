from app.database import db
from app.config import get_config


def test_connection():
    """
    Test the database connection
    """
    config = get_config()
    
    print("Testing database connection...")
    print(f"URI: {config['database']['uri']}")
    print(f"Database: {config['database']['database']}")
    
    try:
        # Get a collection
        collection = db.get_collection("test_collection")
        
        # Insert a test document
        result = collection.insert_one({"test": "connection"})
        print(f"Connection successful! Inserted document with ID: {result.inserted_id}")
        
        # Find the document
        doc = collection.find_one({"test": "connection"})
        print(f"Found document: {doc}")
        
        # Remove the test document
        collection.delete_one({"_id": result.inserted_id})
        print("Test document removed.")
        
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    test_connection() 