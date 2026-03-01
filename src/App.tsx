import React, { useState } from 'react';
import { FolderTree, FileCode2, Package, Database, ChevronRight, ChevronDown, Terminal } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'structure' | 'deps' | 'abc' | 'model'>('structure');

  const tabs = [
    { id: 'structure', label: 'Folder Structure', icon: FolderTree },
    { id: 'deps', label: 'Dependencies', icon: Package },
    { id: 'abc', label: 'Base Generator (ABC)', icon: FileCode2 },
    { id: 'model', label: 'Pydantic Model', icon: Database },
  ] as const;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-sans selection:bg-emerald-500/30">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-2">
            <Terminal className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">
              CK3 Character History Generator
            </h1>
          </div>
          <p className="text-zinc-400 text-sm">
            Architecture Proposal: Tauri (Rust) + React (Frontend) + FastAPI (Python Sidecar)
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Sidebar Navigation */}
          <nav className="w-full md:w-64 shrink-0 flex flex-col gap-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Content Area */}
          <div className="flex-1 min-w-0">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/80 flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                  <div className="w-3 h-3 rounded-full bg-zinc-700" />
                </div>
                <span className="ml-4 text-xs font-mono text-zinc-500">
                  {activeTab === 'structure' && 'project-structure.txt'}
                  {activeTab === 'deps' && 'dependencies'}
                  {activeTab === 'abc' && 'backend/core/base_generator.py'}
                  {activeTab === 'model' && 'backend/models/character.py'}
                </span>
              </div>
              <div className="p-6 overflow-x-auto">
                {activeTab === 'structure' && <FolderStructure />}
                {activeTab === 'deps' && <Dependencies />}
                {activeTab === 'abc' && <BaseGeneratorCode />}
                {activeTab === 'model' && <PydanticModelCode />}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function FolderStructure() {
  const structure = `CK3-Generator/
├── backend/                     # Python Sidecar (FastAPI)
│   ├── main.py                  # FastAPI application entry point
│   ├── requirements.txt         # Python dependencies
│   ├── core/                    # Shared core logic
│   │   ├── __init__.py
│   │   ├── base_generator.py    # Abstract Base Classes (ABCs)
│   │   └── config.py            # Configuration management
│   ├── models/                  # Pydantic models
│   │   ├── __init__.py
│   │   └── character.py         # CK3Character model
│   ├── generators/              # Implementations of generators
│   │   ├── __init__.py
│   │   ├── character_gen.py     # Concrete Character Generator
│   │   └── dynasty_gen.py       # Concrete Dynasty Generator
│   └── api/                     # FastAPI routers
│       ├── __init__.py
│       └── routes.py            # API endpoints
├── src-tauri/                   # Tauri Rust backend
│   ├── Cargo.toml               # Rust dependencies
│   ├── src/
│   │   └── main.rs              # Tauri entry point & sidecar manager
│   └── tauri.conf.json          # Tauri config, including sidecar setup
├── src/                         # React Frontend (Vite)
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/              # React UI components
│   └── services/                # API client for FastAPI
├── package.json                 # Frontend dependencies
└── tsconfig.json                # TypeScript configuration`;

  return (
    <pre className="text-sm font-mono text-zinc-300 leading-relaxed">
      <code>{structure}</code>
    </pre>
  );
}

function Dependencies() {
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-sm font-semibold text-emerald-400 mb-3 uppercase tracking-wider">backend/requirements.txt</h3>
        <pre className="text-sm font-mono text-zinc-300 bg-zinc-950 p-4 rounded-xl border border-zinc-800">
          <code>{`fastapi>=0.110.0
uvicorn>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.2.0`}</code>
        </pre>
      </div>
      <div>
        <h3 className="text-sm font-semibold text-emerald-400 mb-3 uppercase tracking-wider">package.json (Frontend)</h3>
        <pre className="text-sm font-mono text-zinc-300 bg-zinc-950 p-4 rounded-xl border border-zinc-800">
          <code>{`{
  "dependencies": {
    "@tauri-apps/api": "^2.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.546.0",
    "axios": "^1.6.7"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0",
    "typescript": "~5.8.2",
    "vite": "^6.2.0",
    "tailwindcss": "^4.1.14"
  }
}`}</code>
        </pre>
      </div>
    </div>
  );
}

function BaseGeneratorCode() {
  const code = `from abc import ABC, abstractmethod
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
        pass`;

  return (
    <pre className="text-sm font-mono text-zinc-300 leading-relaxed">
      <code>{code}</code>
    </pre>
  );
}

function PydanticModelCode() {
  const code = `from pydantic import BaseModel, Field
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
    is_female: bool = Field(default=False, description="True if character is female")`;

  return (
    <pre className="text-sm font-mono text-zinc-300 leading-relaxed">
      <code>{code}</code>
    </pre>
  );
}
