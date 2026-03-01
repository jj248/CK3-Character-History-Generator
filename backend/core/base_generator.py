from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseGenerator(ABC, Generic[T]):
    """
    Abstract Base Class for all CK3 Generator Components.
    Ensures a consistent interface for generating game entities.
    """
    
    @abstractmethod
    def generate_script(self, entity: T) -> str:
        """
        Generates the CK3 script string for the given entity.
        
        Args:
            entity (T): The Pydantic model representing the entity.
            
        Returns:
            str: The formatted CK3 script string.
        """
        pass
        
    @abstractmethod
    def validate(self, entity: T) -> bool:
        """
        Validates the generated entity against game rules.
        
        Args:
            entity (T): The generated entity to validate.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        pass
