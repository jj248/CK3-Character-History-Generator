from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class LifeStage(str, Enum):
    INFANT = "infant"
    CHILD = "child"
    ADULT = "adult"
    SENIOR = "senior"

class CK3Character(BaseModel):
    id: str
    name: str
    dynasty_id: str
    birth_year: int
    death_year: Optional[int] = None
    father_id: Optional[str] = None
    mother_id: Optional[str] = None
    spouse_id: Optional[str] = None
    is_alive: bool = True
    life_stage: LifeStage = LifeStage.INFANT
    traits: List[str] = Field(default_factory=list)

class CK3Dynasty(BaseModel):
    id: str
    name: str
    founder_id: Optional[str] = None
