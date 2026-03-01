/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Download, FileText, Activity, Settings, Network, Terminal } from 'lucide-react';
import { Graphviz } from '@hpcc-js/wasm';

export default function App() {
  const [activeTab, setActiveTab] = useState<'simulation' | 'config' | 'tree'>('simulation');
  const [logs, setLogs] = useState<string[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [dotContent, setDotContent] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Config States
  const [startYear, setStartYear] = useState(1066);
  const [endYear, setEndYear] = useState(1100);
  const [dynastyName, setDynastyName] = useState('de Normandie');
  const [founderName, setFounderName] = useState('William');

  const [lifeStagesConfig, setLifeStagesConfig] = useState(JSON.stringify({
    mortality_rates: { infant: 0.15, child: 0.05, adult: 0.02, senior: 0.20 },
    marriage_rates: { adult: 0.10 },
    fertility_rates: { adult: 0.15 }
  }, null, 2));

  const [traitsConfig, setTraitsConfig] = useState(JSON.stringify({
    traits: {
      genius: { inheritance_chance: 0.15, mutation_chance: 0.01 },
      strong: { inheritance_chance: 0.10, mutation_chance: 0.02 },
      beautiful: { inheritance_chance: 0.10, mutation_chance: 0.02 }
    }
  }, null, 2));

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Render Graphviz
  useEffect(() => {
    if (dotContent) {
      const renderGraph = async () => {
        try {
          const graphviz = await Graphviz.load();
          const svg = graphviz.layout(dotContent, "svg", "dot");
          setSvgContent(svg);
        } catch (err) {
          console.error("Failed to render graphviz", err);
        }
      };
      renderGraph();
    }
  }, [dotContent]);

  const startSimulation = () => {
    setIsSimulating(true);
    setLogs([]);
    setDotContent(null);
    setSvgContent(null);
    setActiveTab('simulation');

    // In a real Tauri/FastAPI environment, this would connect to the Python backend via SSE:
    // const eventSource = new EventSource(`http://localhost:8000/simulation/run`);
    // eventSource.onmessage = (event) => { ... }
    
    // For this web preview, we simulate the SSE stream locally
    simulateLocally(startYear, endYear);
  };

  const simulateLocally = (start: number, end: number) => {
    let currentYear = start;
    let charId = 2;
    const characters: any[] = [
      { id: '1', name: founderName, birthYear: start - 20, isAlive: true, spouseId: null, traits: ['genius'] }
    ];

    let parsedTraitsConfig: any = {};
    let parsedLifeStagesConfig: any = {};
    try {
      parsedTraitsConfig = JSON.parse(traitsConfig).traits;
      parsedLifeStagesConfig = JSON.parse(lifeStagesConfig);
    } catch (e) {
      setLogs(prev => [...prev, "Error parsing config JSON. Using defaults."]);
      parsedTraitsConfig = {
        genius: { inheritance_chance: 0.15, mutation_chance: 0.01 },
        strong: { inheritance_chance: 0.10, mutation_chance: 0.02 },
        beautiful: { inheritance_chance: 0.10, mutation_chance: 0.02 }
      };
      parsedLifeStagesConfig = {
        mortality_rates: { infant: 0.15, child: 0.05, adult: 0.02, senior: 0.20 },
        marriage_rates: { adult: 0.10 },
        fertility_rates: { adult: 0.15 }
      };
    }

    const inheritTraits = (father: any, mother: any) => {
      const inherited: string[] = [];
      const parentTraits = new Set([...(father.traits || []), ...(mother.traits || [])]);
      
      Object.entries(parsedTraitsConfig).forEach(([trait, rules]: [string, any]) => {
        if (parentTraits.has(trait)) {
          if (Math.random() < rules.inheritance_chance) inherited.push(trait);
        } else {
          if (Math.random() < rules.mutation_chance) inherited.push(trait);
        }
      });
      return inherited;
    };

    const interval = setInterval(() => {
      if (currentYear > end) {
        clearInterval(interval);
        setIsSimulating(false);
        generateDotFile(characters);
        setLogs(prev => [...prev, `Simulation complete. Files written to Dynasty Preview/`]);
        return;
      }

      const yearLogs: string[] = [`Year ${currentYear} begins.`];
      
      const living = characters.filter(c => c.isAlive);
      living.forEach(char => {
        const age = currentYear - char.birthYear;
        let lifeStage = 'infant';
        if (age >= 3 && age < 16) lifeStage = 'child';
        else if (age >= 16 && age < 50) lifeStage = 'adult';
        else if (age >= 50) lifeStage = 'senior';
        
        // Death
        const mortalityRate = parsedLifeStagesConfig.mortality_rates[lifeStage] || 0.01;
        if (Math.random() < mortalityRate) {
          char.isAlive = false;
          char.deathYear = currentYear;
          yearLogs.push(`Year ${currentYear}: Character ${char.name} (${char.id}) died at age ${age}.`);
          return;
        }

        // Marriage
        if (lifeStage === 'adult' && !char.spouseId && Math.random() < (parsedLifeStagesConfig.marriage_rates.adult || 0.1)) {
          const eligible = living.filter(c => c.id !== char.id && c.isAlive && !c.spouseId && (currentYear - c.birthYear) >= 16);
          if (eligible.length > 0) {
            const spouse = eligible[Math.floor(Math.random() * eligible.length)];
            char.spouseId = spouse.id;
            spouse.spouseId = char.id;
            yearLogs.push(`Year ${currentYear}: Character ${char.name} (${char.id}) married ${spouse.name} (${spouse.id}).`);
          }
        }

        // Conception
        if (char.spouseId && lifeStage === 'adult' && age < 50 && Math.random() < (parsedLifeStagesConfig.fertility_rates.adult || 0.15)) {
          if (parseInt(char.id) < parseInt(char.spouseId)) {
            const spouse = characters.find(c => c.id === char.spouseId);
            const childTraits = inheritTraits(char, spouse);
            
            const child = {
              id: String(charId++),
              name: `Child_${charId - 1}`,
              birthYear: currentYear,
              isAlive: true,
              spouseId: null,
              fatherId: char.id,
              motherId: char.spouseId,
              traits: childTraits
            };
            characters.push(child);
            const traitStr = childTraits.length > 0 ? ` with traits: ${childTraits.join(', ')}` : '';
            yearLogs.push(`Year ${currentYear}: Character ${char.name} (${char.id}) and ${spouse.name} had a child: ${child.name} (${child.id})${traitStr}.`);
          }
        }
      });

      setLogs(prev => [...prev, ...yearLogs]);
      currentYear++;
    }, 100);
  };

  const generateDotFile = (characters: any[]) => {
    let dot = 'digraph FamilyTree {\n';
    dot += '    node [shape=box, fontname="Helvetica", style="filled", fillcolor="#1e1e24", fontcolor="#e2e8f0", color="#3f3f46"];\n';
    dot += '    edge [fontname="Helvetica", color="#71717a"];\n';
    dot += '    bgcolor="transparent";\n';
    
    characters.forEach(char => {
      const traitStr = char.traits && char.traits.length > 0 ? `\\n[${char.traits.join(', ')}]` : '';
      const label = `${char.name}\\n(${char.birthYear} - ${char.deathYear || 'Present'})${traitStr}`;
      dot += `    "${char.id}" [label="${label}"];\n`;
      if (char.fatherId) dot += `    "${char.fatherId}" -> "${char.id}" [label="Father"];\n`;
      if (char.motherId) dot += `    "${char.motherId}" -> "${char.id}" [label="Mother"];\n`;
    });
    
    dot += '}\n';
    setDotContent(dot);
  };

  const downloadDot = () => {
    if (!dotContent) return;
    const blob = new Blob(['\ufeff' + dotContent], { type: 'text/vnd.graphviz;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'family_tree.dot';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-300 font-mono p-6 flex flex-col">
      <div className="max-w-6xl mx-auto w-full space-y-6 flex-1 flex flex-col">
        <header className="border-b border-zinc-800 pb-4 flex justify-between items-end">
          <div>
            <h1 className="text-2xl font-bold text-zinc-100 flex items-center gap-2">
              <Activity className="w-6 h-6 text-emerald-500" />
              CK3 Dynasty Simulator Engine
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              Procedural History Simulation Engine (Tauri + React UI)
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('simulation')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'simulation' ? 'bg-zinc-800 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'}`}
            >
              <Terminal className="w-4 h-4" /> Console
            </button>
            <button
              onClick={() => setActiveTab('config')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'config' ? 'bg-zinc-800 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'}`}
            >
              <Settings className="w-4 h-4" /> Config
            </button>
            <button
              onClick={() => setActiveTab('tree')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'tree' ? 'bg-zinc-800 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'}`}
            >
              <Network className="w-4 h-4" /> Tree Viewer
            </button>
          </div>
        </header>

        <div className="flex-1 flex gap-6 min-h-[600px]">
          {/* Sidebar Controls */}
          <div className="w-80 space-y-6 flex-shrink-0">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 className="text-lg font-semibold text-zinc-100 mb-4">Initialization</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">Start Year</label>
                    <input 
                      type="number" 
                      value={startYear}
                      onChange={(e) => setStartYear(parseInt(e.target.value))}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">End Year</label>
                    <input 
                      type="number" 
                      value={endYear}
                      onChange={(e) => setEndYear(parseInt(e.target.value))}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Dynasty Name</label>
                  <input 
                    type="text" 
                    value={dynastyName}
                    onChange={(e) => setDynastyName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Founder Name</label>
                  <input 
                    type="text" 
                    value={founderName}
                    onChange={(e) => setFounderName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
                  />
                </div>
                
                <button
                  onClick={startSimulation}
                  disabled={isSimulating}
                  className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4"
                >
                  {isSimulating ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {isSimulating ? 'Simulating...' : 'Start Simulation'}
                </button>
              </div>
            </div>

            {dotContent && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <h2 className="text-lg font-semibold text-zinc-100 mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-400" />
                  Export
                </h2>
                <p className="text-xs text-zinc-500 mb-4">
                  Graphviz DOT file generated with UTF-8 BOM.
                </p>
                <button
                  onClick={downloadDot}
                  className="w-full flex items-center justify-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded px-4 py-2 text-sm font-medium transition-colors border border-zinc-700"
                >
                  <Download className="w-4 h-4" />
                  Download .dot File
                </button>
              </div>
            )}
          </div>

          {/* Main Content Area */}
          <div className="flex-1 bg-zinc-900 border border-zinc-800 rounded-lg flex flex-col overflow-hidden">
            {activeTab === 'simulation' && (
              <>
                <div className="p-3 border-b border-zinc-800 bg-zinc-950/50 flex justify-between items-center">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Live Console (SSE Stream)</span>
                  <span className="flex items-center gap-2 text-xs text-zinc-500">
                    <span className={`w-2 h-2 rounded-full ${isSimulating ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`}></span>
                    {isSimulating ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-xs">
                  {logs.length === 0 ? (
                    <div className="text-zinc-600 italic">Waiting for simulation to start...</div>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className={`${log.includes('died') ? 'text-red-400' : log.includes('married') ? 'text-blue-400' : log.includes('child') ? 'text-emerald-400' : 'text-zinc-400'}`}>
                        <span className="text-zinc-600 mr-2">[{new Date().toISOString().split('T')[1].split('.')[0]}]</span>
                        {log}
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </>
            )}

            {activeTab === 'config' && (
              <div className="flex-1 flex flex-col">
                <div className="p-3 border-b border-zinc-800 bg-zinc-950/50">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">JSON Configuration Editors</span>
                </div>
                <div className="flex-1 p-4 grid grid-cols-2 gap-4 overflow-y-auto">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-zinc-300">life_stages.json</label>
                    <textarea 
                      value={lifeStagesConfig}
                      onChange={(e) => setLifeStagesConfig(e.target.value)}
                      className="w-full h-96 bg-zinc-950 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-zinc-300">traits.json</label>
                    <textarea 
                      value={traitsConfig}
                      onChange={(e) => setTraitsConfig(e.target.value)}
                      className="w-full h-96 bg-zinc-950 border border-zinc-800 rounded p-3 text-xs font-mono text-zinc-300 focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div className="col-span-2 text-xs text-zinc-500 italic">
                    Note: In the full Tauri app, these changes are saved directly to the /config directory using Rust file APIs.
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'tree' && (
              <div className="flex-1 flex flex-col">
                <div className="p-3 border-b border-zinc-800 bg-zinc-950/50 flex justify-between items-center">
                  <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Graphviz Tree Viewer</span>
                </div>
                <div className="flex-1 overflow-auto bg-zinc-950 p-4 flex items-center justify-center">
                  {svgContent ? (
                    <div 
                      dangerouslySetInnerHTML={{ __html: svgContent }} 
                      className="max-w-full max-h-full"
                    />
                  ) : (
                    <div className="text-zinc-600 italic">
                      {isSimulating ? 'Simulation in progress...' : 'Run a simulation to view the family tree.'}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
