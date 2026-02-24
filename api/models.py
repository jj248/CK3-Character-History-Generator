"""
Pydantic models for the CK3 Character History Generator API.

These models validate incoming PUT request bodies before anything is written
to disk. All constraints mirror ConfigLoader.validate_configs() exactly, so a
payload that passes here will also pass the Python-side validation when the
simulation runs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
#  Shared primitives
# ---------------------------------------------------------------------------

# Rate arrays must have exactly 121 entries (ages 0–120).
RateList = Annotated[list[float], Field(min_length=121, max_length=121)]


# ---------------------------------------------------------------------------
#  Initialization config models
# ---------------------------------------------------------------------------


class NameInheritance(BaseModel):
    """Probability weights for how a child's name is chosen."""

    grandparentNameInheritanceChance: float = Field(ge=0.0, le=1.0)
    parentNameInheritanceChance: float = Field(ge=0.0, le=1.0)
    noNameInheritanceChance: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def chances_sum_to_one(self) -> NameInheritance:
        total = (
            self.grandparentNameInheritanceChance
            + self.parentNameInheritanceChance
            + self.noNameInheritanceChance
        )
        if abs(total - 1.0) >= 1e-6:
            raise ValueError(
                f"nameInheritance chances must sum to 1.0 (got {total:.6f})."
            )
        return self


class NegativeEvent(BaseModel):
    """A historical event that raises the death rate within a date/age window."""

    eventID: str = Field(min_length=1)
    startYear: int
    endYear: int
    deathReason: str = Field(min_length=1)
    deathMultiplier: float = Field(gt=0.0)
    characterAgeStart: int = Field(ge=0)
    characterAgeEnd: int = Field(ge=0)

    @model_validator(mode="after")
    def end_after_start(self) -> NegativeEvent:
        if self.endYear < self.startYear:
            raise ValueError("endYear must be greater than or equal to startYear.")
        if self.characterAgeEnd < self.characterAgeStart:
            raise ValueError(
                "characterAgeEnd must be greater than or equal to characterAgeStart."
            )
        return self


class Dynasty(BaseModel):
    """A single dynasty definition inside initialization.json."""

    dynastyID: str = Field(min_length=1)
    dynastyName: str = Field(min_length=1)
    dynastyMotto: str = ""
    succession: str = Field(min_length=1)
    isHouse: bool = False
    faithID: str = Field(min_length=1)
    cultureID: str = Field(min_length=1)
    gender_law: str = Field(min_length=1)
    progenitorMaleBirthYear: int
    allowFirstCousinMarriage: bool = False
    prioritiseLowbornMarriage: bool = False
    numenorBloodTier: int | None = None
    # Each entry is a comma-separated "language_id,start_year,end_year" string.
    languages: list[str] = Field(default_factory=list)
    nameInheritance: NameInheritance


class InitializationConfig(BaseModel):
    """Full shape of config/initialization.json."""

    dynasties: list[Dynasty] = Field(min_length=1)
    events: list[NegativeEvent] = Field(default_factory=list)
    minYear: int
    maxYear: int
    generationMax: int = Field(gt=0)
    initialCharID: int = Field(gt=0)

    @model_validator(mode="after")
    def max_year_after_min(self) -> InitializationConfig:
        if self.maxYear <= self.minYear:
            raise ValueError("maxYear must be greater than minYear.")
        return self

    # Allow unknown extra keys so forward-compatible config fields aren't
    # silently dropped when the frontend round-trips the JSON.
    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
#  Life stages config models
# ---------------------------------------------------------------------------


class RateSet(BaseModel):
    """A pair of Male/Female rate arrays, each covering ages 0–120."""

    Male: RateList
    Female: RateList


class LifeStagesConfig(BaseModel):
    """Full shape of config/life_stages.json."""

    mortalityRates: RateSet
    marriageRates: RateSet
    fertilityRates: RateSet
    desperationMarriageRates: list[float]
    marriageMaxAgeDifference: int = Field(ge=0)
    maximumNumberOfChildren: int = Field(ge=0)
    minimumYearsBetweenChildren: int = Field(ge=0)
    bastardyChanceMale: float = Field(ge=0.0, le=1.0)
    bastardyChanceFemale: float = Field(ge=0.0, le=1.0)

    @field_validator("mortalityRates", "marriageRates", "fertilityRates", mode="after")
    @classmethod
    def rates_are_probabilities(cls, rate_set: RateSet) -> RateSet:
        """Every individual rate must be in [0.0, 1.0]."""
        for sex, rates in (("Male", rate_set.Male), ("Female", rate_set.Female)):
            for i, v in enumerate(rates):
                if not (0.0 <= v <= 1.0):
                    raise ValueError(
                        f"{sex} rate at index {i} is {v!r}; must be between 0.0 and 1.0."
                    )
        return rate_set

    model_config = {"extra": "allow"}