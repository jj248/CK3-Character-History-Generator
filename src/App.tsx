import React, { useState } from 'react';
import { Terminal, Save, Play, FileCode2, Info } from 'lucide-react';
import { CK3Character, GenerationResponse } from './types';

export default function App() {
  const [formData, setFormData] = useState<CK3Character>({
    id: 'char_1001',
    name: 'Leon',
    dynasty_id: 'dyn_456',
    culture: 'french',
    religion: 'catholic',
    traits: ['brave', 'ambitious'],
    stats: {
      diplomacy: 5,
      martial: 8,
      stewardship: 4,
      intrigue: 6,
      learning: 3,
      prowess: 10
    },
    birth_date: '1066.1.1',
    death_date: '',
    is_female: false
  });

  const [preview, setPreview] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleStatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      stats: {
        ...prev.stats,
        [name]: parseInt(value) || 0
      }
    }));
  };

  const handleTraitsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const traitsArray = e.target.value.split(',').map(t => t.trim()).filter(Boolean);
    setFormData(prev => ({ ...prev, traits: traitsArray }));
  };

  const generateMockScript = (char: CK3Character) => {
    const lines = [];
    lines.push(`${char.id} = {`);
    lines.push(`\tname = "${char.name}"`);
    if (char.is_female) lines.push(`\tfemale = yes`);
    if (char.dynasty_id) lines.push(`\tdynasty = ${char.dynasty_id}`);
    lines.push(`\tculture = ${char.culture}`);
    lines.push(`\treligion = ${char.religion}`);
    char.traits.forEach(t => lines.push(`\ttrait = ${t}`));
    
    const s = char.stats;
    if (s.diplomacy || s.martial || s.stewardship || s.intrigue || s.learning || s.prowess) {
      lines.push(`\tdiplomacy = ${s.diplomacy}`);
      lines.push(`\tmartial = ${s.martial}`);
      lines.push(`\tstewardship = ${s.stewardship}`);
      lines.push(`\tintrigue = ${s.intrigue}`);
      lines.push(`\tlearning = ${s.learning}`);
      lines.push(`\tprowess = ${s.prowess}`);
    }
    
    lines.push(`\t${char.birth_date} = {\n\t\tbirth = yes\n\t}`);
    if (char.death_date) {
      lines.push(`\t${char.death_date} = {\n\t\tdeath = yes\n\t}`);
    }
    lines.push(`}`);
    return lines.join('\n');
  };

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // In a real Tauri app, this would hit the Python sidecar running on localhost
      const response = await fetch('http://localhost:8000/generate/character', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to connect to FastAPI Sidecar');
      }
      
      const data: GenerationResponse = await response.json();
      setPreview(data.script);
    } catch (err) {
      // Fallback for the web preview environment where the sidecar isn't running
      console.warn("FastAPI sidecar not reachable, using mock generation for preview.", err);
      setError("FastAPI sidecar not reachable. Showing local preview.");
      setPreview(generateMockScript(formData));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-950 text-stone-300 font-sans selection:bg-amber-900/50">
      {/* Header */}
      <header className="border-b border-stone-800/60 bg-stone-900/80 backdrop-blur-md sticky top-0 z-10 shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-900/20 border border-amber-700/30 flex items-center justify-center">
              <FileCode2 className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-semibold text-amber-50 tracking-wide">
                CK3 Character History Generator
              </h1>
              <p className="text-amber-700/80 text-xs uppercase tracking-widest font-semibold">
                Tauri Sidecar Architecture
              </p>
            </div>
          </div>
          
          <button 
            onClick={handleGenerate}
            disabled={isLoading}
            className="flex items-center gap-2 bg-amber-700 hover:bg-amber-600 text-amber-50 px-5 py-2.5 rounded-sm font-serif font-medium transition-colors border border-amber-500/30 shadow-lg shadow-amber-900/20 disabled:opacity-50"
          >
            {isLoading ? <Terminal className="w-4 h-4 animate-pulse" /> : <Play className="w-4 h-4" />}
            Generate Script
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Form Section */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-stone-900/50 border border-stone-800 rounded-sm p-6 shadow-inner">
              <h2 className="text-xl font-serif text-amber-100 mb-6 flex items-center gap-2 border-b border-stone-800 pb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                Character Details
              </h2>
              
              <div className="grid grid-cols-2 gap-5">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Character ID</label>
                  <input 
                    type="text" name="id" value={formData.id} onChange={handleInputChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-mono text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Name</label>
                  <input 
                    type="text" name="name" value={formData.name} onChange={handleInputChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-serif text-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Dynasty ID</label>
                  <input 
                    type="text" name="dynasty_id" value={formData.dynasty_id || ''} onChange={handleInputChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-mono text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Culture</label>
                  <input 
                    type="text" name="culture" value={formData.culture} onChange={handleInputChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Religion</label>
                  <input 
                    type="text" name="religion" value={formData.religion} onChange={handleInputChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Traits (comma separated)</label>
                  <input 
                    type="text" value={formData.traits.join(', ')} onChange={handleTraitsChange}
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Birth Date</label>
                  <input 
                    type="text" name="birth_date" value={formData.birth_date} onChange={handleInputChange} placeholder="YYYY.MM.DD"
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-mono text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Death Date</label>
                  <input 
                    type="text" name="death_date" value={formData.death_date || ''} onChange={handleInputChange} placeholder="YYYY.MM.DD"
                    className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-mono text-sm"
                  />
                </div>
                <div className="col-span-2 flex items-center gap-3 mt-2">
                  <input 
                    type="checkbox" name="is_female" id="is_female" checked={formData.is_female} onChange={handleInputChange}
                    className="w-4 h-4 rounded-sm border-stone-700 text-amber-600 focus:ring-amber-600/50 bg-stone-950"
                  />
                  <label htmlFor="is_female" className="text-sm font-medium text-stone-300">Is Female Character</label>
                </div>
              </div>
            </div>

            <div className="bg-stone-900/50 border border-stone-800 rounded-sm p-6 shadow-inner">
              <h2 className="text-xl font-serif text-amber-100 mb-6 flex items-center gap-2 border-b border-stone-800 pb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                Base Stats
              </h2>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(formData.stats).map(([stat, value]) => (
                  <div key={stat} className="space-y-1.5">
                    <label className="text-xs font-semibold text-stone-400 uppercase tracking-wider flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        stat === 'diplomacy' ? 'bg-blue-500' :
                        stat === 'martial' ? 'bg-red-500' :
                        stat === 'stewardship' ? 'bg-green-500' :
                        stat === 'intrigue' ? 'bg-purple-500' :
                        stat === 'learning' ? 'bg-stone-300' : 'bg-orange-500'
                      }`} />
                      {stat}
                    </label>
                    <input 
                      type="number" min="0" name={stat} value={value} onChange={handleStatChange}
                      className="w-full bg-stone-950 border border-stone-800 rounded-sm px-3 py-2 text-stone-200 focus:outline-none focus:border-amber-700/50 focus:ring-1 focus:ring-amber-700/50 transition-all font-mono text-center"
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Preview Section */}
          <div className="lg:col-span-5 h-[calc(100vh-12rem)] sticky top-28">
            <div className="bg-[#1e1e1e] border border-stone-800 rounded-sm shadow-2xl h-full flex flex-col overflow-hidden">
              <div className="px-4 py-3 border-b border-stone-800 bg-[#252526] flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-stone-400" />
                  <span className="text-xs font-mono text-stone-300">output/preview.txt</span>
                </div>
                {error && (
                  <div className="flex items-center gap-1.5 text-amber-500/80 text-xs">
                    <Info className="w-3.5 h-3.5" />
                    <span>Local Preview Mode</span>
                  </div>
                )}
              </div>
              <div className="flex-1 p-4 overflow-auto bg-[#1e1e1e]">
                {preview ? (
                  <pre className="text-[13px] font-mono leading-relaxed text-[#d4d4d4]">
                    <code dangerouslySetInnerHTML={{
                      __html: preview
                        .replace(/(\w+)\s*=/g, '<span class="text-[#9cdcfe]">$1</span> =')
                        .replace(/"([^"]*)"/g, '<span class="text-[#ce9178]">"$1"</span>')
                        .replace(/= (yes|no)/g, '= <span class="text-[#569cd6]">$1</span>')
                        .replace(/= (\d+)/g, '= <span class="text-[#b5cea8]">$1</span>')
                    }} />
                  </pre>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-stone-600 space-y-3">
                    <FileCode2 className="w-12 h-12 opacity-20" />
                    <p className="text-sm font-serif">Click Generate to view the CK3 script</p>
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

