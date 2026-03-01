from pydantic import BaseModel, Field
from typing import List, Optional

class CharacterStats(BaseModel):
    """CK3 Character Base Stats"""
    diplomacy: int = Field(default=0, ge=0, description="Diplomacy skill")
    martial: int = Field(default=0, ge=0, description="Martial skill")
    stewardship: int = Field(default=0, ge=0, description="Stewardship skill")
    intrigue: int = Field(default=0, ge=0, description="Intrigue skill")
    learning: int = Field(default=0, ge=0, description="Learning skill")
    prowess: int = Field(default=0, ge=0, description="Prowess skill")

class CK3Character(BaseModel):
    """
    Strictly typed model representing a CK3 Character.
    """
    id: str = Field(..., description="Unique character identifier")
    name: str = Field(..., min_length=1, description="Character's first name")
    dynasty_id: Optional[str] = Field(None, description="ID of the character's dynasty")
    culture: str = Field(..., description="Character's culture ID")
    religion: str = Field(..., description="Character's religion/faith ID")
    traits: List[str] = Field(default_factory=list, description="List of trait IDs")
    stats: CharacterStats = Field(default_factory=CharacterStats, description="Character's base stats")
    birth_date: str = Field(..., description="Birth date in YYYY.MM.DD format")
    death_date: Optional[str] = Field(None, description="Death date in YYYY.MM.DD format")
    is_female: bool = Field(default=False, description="True if character is female")