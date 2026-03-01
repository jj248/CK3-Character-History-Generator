from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from backend.models.character import CK3Character
from backend.generators.character_gen import CharacterHistoryGenerator
from backend.services.character_service import CharacterService

app = FastAPI(
    title="CK3 Character History Generator API",
    description="API for generating Crusader Kings 3 character history scripts.",
    version="1.0.0"
)

class GenerationResponse(BaseModel):
    """Response model for generation endpoints."""
    message: str
    file_path: str
    script: str

@app.post("/generate/character", response_model=GenerationResponse)
def generate_character(character: CK3Character) -> GenerationResponse:
    """
    Generates a CK3 character history script and saves it to a file.

    Args:
        character (CK3Character): The character data payload.

    Returns:
        GenerationResponse: The generation result including the script and file path.
    """
    generator = CharacterHistoryGenerator()
    
    if not generator.validate(character):
        raise HTTPException(status_code=400, detail="Invalid character data provided.")
        
    script = generator.generate_script(character)
    
    service = CharacterService()
    output_dir = os.path.join(os.getcwd(), "output")
    output_path = os.path.join(output_dir, f"{character.id}_history.txt")
    
    try:
        saved_path = service.save_character_history(script, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return GenerationResponse(
        message="Character history generated successfully.",
        file_path=saved_path,
        script=script
    )
