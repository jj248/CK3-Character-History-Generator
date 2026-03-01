from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from engine import SimulationEngine, HumanLifeStageStrategy
from models import CK3Character, CK3Dynasty
from export import export_graphviz
from config_manager import ConfigManager
from file_io import FileIOService
import asyncio
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/simulation/run")
async def run_simulation():
    config_manager = ConfigManager("config")
    engine = SimulationEngine(config_manager, HumanLifeStageStrategy())

    init_config = config_manager.get_initialization()
    start_year = init_config.get("start_year", 1066)
    end_year = init_config.get("end_year", 1100)
    dynasty_name = init_config.get("dynasty_name", "House of Founders")
    founder_name = init_config.get("founder_name", "Founder")

    # Initialize with a founder
    founder = CK3Character(
        id="1",
        name=founder_name,
        dynasty_id="1",
        birth_year=start_year - 20,
        life_stage="adult",
        traits=["genius"]
    )
    engine.add_character(founder)
    engine.add_dynasty(CK3Dynasty(id="1", name=dynasty_name, founder_id="1"))
    engine.next_char_id = 2

    async def event_generator():
        for log in engine.run_simulation(start_year, end_year):
            yield f"data: {json.dumps({'log': log})}\n\n"
            await asyncio.sleep(0.01)
        
        # Export Graphviz
        dot_content = export_graphviz(engine.characters, engine.dynasties)
        yield f"data: {json.dumps({'dot': dot_content})}\n\n"
        
        # File I/O
        io_service = FileIOService("Dynasty Preview")
        io_service.write_characters(engine.characters)
        io_service.write_dynasties(engine.dynasties)
        
        yield f"data: {json.dumps({'log': 'Simulation complete. Files written to Dynasty Preview/'})}\n\n"
        yield "data: [DONE]\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
