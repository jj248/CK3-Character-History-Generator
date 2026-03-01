// Typed wrappers around every FastAPI endpoint.
// In development the Vite proxy rewrites /api -> http://127.0.0.1:8000.
// In the packaged app the sidecar is already bound on port 8000 so the
// same base URL works without modification.

const BASE = "/api";

// ---------------------------------------------------------------------------
//  Shared types
// ---------------------------------------------------------------------------

export interface NameInheritance {
  grandparentNameInheritanceChance: number;
  parentNameInheritanceChance: number;
  noNameInheritanceChance: number;
}

export interface Dynasty {
  dynastyID: string;
  dynastyName: string;
  dynastyMotto: string;
  succession: string;
  isHouse: boolean;
  faithID: string;
  cultureID: string;
  gender_law: string;
  progenitorMaleBirthYear: number;
  allowFirstCousinMarriage: boolean;
  prioritiseLowbornMarriage: boolean;
  forceDynastyAlive: boolean;
  numenorBloodTier?: number;
  languages?: string[];
  nameInheritance: NameInheritance;
}

export interface NegativeEvent {
  eventID: string;
  startYear: number;
  endYear: number;
  deathReason: string;
  deathMultiplier: number;
  characterAgeStart: number;
  characterAgeEnd: number;
}

export interface InitializationConfig {
  dynasties: Dynasty[];
  events: NegativeEvent[];
  minYear: number;
  maxYear: number;
  generationMax: number;
  initialCharID: number;
  [key: string]: unknown;
}

export interface RateSet {
  Male: number[];
  Female: number[];
}

export interface LifeStagesConfig {
  mortalityRates: RateSet;
  marriageRates: RateSet;
  fertilityRates: RateSet;
  desperationMarriageRates: number[];
  marriageMaxAgeDifference: number;
  maximumNumberOfChildren: number;
  minimumYearsBetweenChildren: number;
  bastardyChanceMale: number;
  bastardyChanceFemale: number;
  [key: string]: unknown;
}

export interface SimulationMessage {
  log?: string;
  error?: string;
  status?: string;
}

// ---------------------------------------------------------------------------
//  Config — Initialization
// ---------------------------------------------------------------------------

export async function fetchInitializationConfig(): Promise<InitializationConfig> {
  const res = await fetch(`${BASE}/config/initialization`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function saveInitializationConfig(
  config: InitializationConfig
): Promise<void> {
  const res = await fetch(`${BASE}/config/initialization`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function resetInitializationConfig(): Promise<void> {
  const res = await fetch(`${BASE}/config/initialization/reset`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function setInitializationFallback(): Promise<void> {
  const res = await fetch(`${BASE}/config/initialization/set-fallback`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
}

// ---------------------------------------------------------------------------
//  Config — Life Stages
// ---------------------------------------------------------------------------

export async function fetchLifeStagesConfig(): Promise<LifeStagesConfig> {
  const res = await fetch(`${BASE}/config/life-stages`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchLifeStagesFallback(): Promise<LifeStagesConfig> {
  const res = await fetch(`${BASE}/config/life-stages/fallback`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function saveLifeStagesConfig(
  config: LifeStagesConfig
): Promise<void> {
  const res = await fetch(`${BASE}/config/life-stages`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(await res.text());
}

export async function resetLifeStagesConfig(): Promise<void> {
  const res = await fetch(`${BASE}/config/life-stages/reset`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await res.text());
}

// ---------------------------------------------------------------------------
//  Images
// ---------------------------------------------------------------------------

export async function fetchImageList(): Promise<string[]> {
  const res = await fetch(`${BASE}/images`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function imageUrl(filename: string): string {
  return `${BASE}/images/${encodeURIComponent(filename)}`;
}

// ---------------------------------------------------------------------------
//  Simulation — SSE streaming run
// ---------------------------------------------------------------------------

export function streamSimulation(
  onMessage: (msg: SimulationMessage) => void,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();

  fetch(`${BASE}/simulation/run`, {
    method: "POST",
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        throw new Error(`Simulation request failed: ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg: SimulationMessage = JSON.parse(line.slice(6));
            onMessage(msg);
            if (msg.status === "complete" || msg.error) {
              onDone();
              return;
            }
          } catch {
            // Ignore malformed SSE lines
          }
        }
      }
      onDone();
    })
    .catch((err: Error) => {
      if (err.name !== "AbortError") onError(err);
    });

  // Return a cancel function
  return () => controller.abort();
}