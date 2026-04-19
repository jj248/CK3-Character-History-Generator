// Typed wrappers around every FastAPI endpoint.
// In development the Vite proxy rewrites /api -> http://127.0.0.1:8000.
// In the packaged app the sidecar is already bound on port 8000 so the
// same base URL works without modification.

const BASE = import.meta.env.PROD ? "http://127.0.0.1:8000" : "/api";

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
//  Retry / health-check utilities
// ---------------------------------------------------------------------------

/**
 * Fetch a URL, retrying on network failure or non-OK responses.
 *
 * Used on startup so the UI waits for the FastAPI sidecar to finish binding
 * its port before attempting to load config. Without this, a race between
 * Tauri spawning the sidecar and the first React render causes the server to
 * return an HTML error page instead of JSON, which surfaces as:
 *   "Failed to load configuration: Unexpected token '<', "<!DOCTYPE "..."
 *
 * @param url     Full URL to fetch.
 * @param retries Maximum number of attempts (default 10).
 * @param delay   Milliseconds to wait between attempts (default 800).
 */
async function fetchWithRetry(
  url: string,
  retries = 10,
  delay = 800
): Promise<Response> {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch(url);
      if (res.ok) return res;
      // A 4xx means the server is up but the request itself is wrong —
      // no point retrying, surface immediately.
      if (res.status >= 400 && res.status < 500) {
        throw new Error(`${res.status} ${res.statusText}`);
      }
      // 5xx or unexpected — fall through to retry.
    } catch (err) {
      if (attempt === retries - 1) throw err;
      console.warn(
        `[api] Connection attempt ${attempt + 1}/${retries} failed — retrying in ${delay}ms`
      );
    }
    await new Promise<void>((resolve) => setTimeout(resolve, delay));
  }
  throw new Error(`Could not connect to the API server after ${retries} attempts.`);
}

/**
 * Poll the API until the sidecar responds, then resolve.
 * Rejects after all retries are exhausted — treat as a fatal startup error.
 */
export async function waitForApi(retries = 10, delay = 800): Promise<void> {
  await fetchWithRetry(`${BASE}/config/initialization`, retries, delay);
}

// ---------------------------------------------------------------------------
//  Config — Initialization
// ---------------------------------------------------------------------------

export async function fetchInitializationConfig(): Promise<InitializationConfig> {
  const res = await fetchWithRetry(`${BASE}/config/initialization`);
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
  const res = await fetchWithRetry(`${BASE}/config/life-stages`);
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