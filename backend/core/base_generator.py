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
    def generate(self, **kwargs: Any) -> T:
        """
        Generates a specific CK3 entity.
        
        Args:
            **kwargs: Generation parameters and constraints.
            
        Returns:
            T: A Pydantic model representing the generated entity.
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
