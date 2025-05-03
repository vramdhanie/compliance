import json
from datetime import datetime
from typing import Any


def json_serialize(obj: Any) -> str:
    """
    Serialize an object to JSON, handling special types like datetime
    
    Args:
        obj: The object to serialize
        
    Returns:
        str: The JSON string
    """
    class CustomEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            # Handle MongoDB ObjectId
            if hasattr(o, '__str__') and str(type(o)) == "<class 'bson.objectid.ObjectId'>":
                return str(o)
            return super().default(o)
            
    return json.dumps(obj, cls=CustomEncoder)


def json_deserialize(json_str: str) -> Any:
    """
    Deserialize a JSON string to an object
    
    Args:
        json_str: The JSON string to deserialize
        
    Returns:
        Any: The deserialized object
    """
    return json.loads(json_str) 