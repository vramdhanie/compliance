from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Tuple
from bson import ObjectId

T = TypeVar('T')

# Type definitions for MongoDB
class Database:
    """Type stub for MongoDB Database"""
    
    def __getitem__(self, name: str) -> 'MongoCollection[Dict[str, Any]]':
        ...
        
    def list_collection_names(self) -> List[str]:
        ...


class MongoCollection(Generic[T]):
    """Type stub for MongoDB Collection"""
    
    def insert_one(self, document: Dict[str, Any]) -> 'InsertOneResult':
        ...
    
    def insert_many(self, documents: List[Dict[str, Any]]) -> 'InsertManyResult':
        ...
    
    def find_one(self, filter: Optional[Dict[str, Any]] = None, *args, **kwargs) -> Optional[Dict[str, Any]]:
        ...
    
    def find(self, filter: Optional[Dict[str, Any]] = None, *args, **kwargs) -> 'Cursor':
        ...
    
    def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs) -> 'UpdateResult':
        ...
    
    def update_many(self, filter: Dict[str, Any], update: Dict[str, Any], *args, **kwargs) -> 'UpdateResult':
        ...
    
    def delete_one(self, filter: Dict[str, Any], *args, **kwargs) -> 'DeleteResult':
        ...
    
    def delete_many(self, filter: Dict[str, Any], *args, **kwargs) -> 'DeleteResult':
        ...
        
    def create_index(self, keys: Union[str, List[Tuple[str, Any]]], unique: bool = False, **kwargs) -> str:
        ...


class InsertOneResult:
    """Type stub for MongoDB InsertOneResult"""
    
    @property
    def inserted_id(self) -> Union[str, ObjectId]:
        ...


class InsertManyResult:
    """Type stub for MongoDB InsertManyResult"""
    
    @property
    def inserted_ids(self) -> List[Union[str, ObjectId]]:
        ...


class UpdateResult:
    """Type stub for MongoDB UpdateResult"""
    
    @property
    def modified_count(self) -> int:
        ...
    
    @property
    def matched_count(self) -> int:
        ...
    
    @property
    def upserted_id(self) -> Optional[Union[str, ObjectId]]:
        ...


class DeleteResult:
    """Type stub for MongoDB DeleteResult"""
    
    @property
    def deleted_count(self) -> int:
        ...


class Cursor:
    """Type stub for MongoDB Cursor"""
    
    def __iter__(self) -> 'Cursor':
        ...
    
    def __next__(self) -> Dict[str, Any]:
        ...
    
    def limit(self, limit: int) -> 'Cursor':
        ...
    
    def skip(self, skip: int) -> 'Cursor':
        ...
    
    def sort(self, key_or_list, direction=None) -> 'Cursor':
        ... 