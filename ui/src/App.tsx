/**
 * App.tsx
 *
 * Root application shell. Loads configuration on mount, renders the tab
 * navigation, and wraps the entire component tree in an ErrorBoundary so
 * unexpected render errors produce a recoverable UI rather than a blank screen.
 */

import { useEffect, useState } from "react";
import {
  waitForApi,
  fetchInitializationConfig,
  fetchLifeStagesConfig,
  InitializationConfig,
  LifeStagesConfig,
} from "./api";
import ErrorBoundary from "./components/ErrorBoundary";
import DynastySettings from "./components/DynastySettings";
import NegativeEvents from "./components/NegativeEvents";
import DynastyTrees from "./components/DynastyTrees";
import LifeCycleModifiers from "./components/LifeCycleModifiers";

// ---------------------------------------------------------------------------
//  Types
// ---------------------------------------------------------------------------

type TabId = "dynasties" | "trees" | "events" | "lifecycle";

const TABS: { id: TabId; label: string }[] = [
  { id: "dynasties", label: "Dynasty Settings" },
  { id: "trees",     label: "Dynasty Trees" },
  { id: "events",    label: "Negative Events" },
  { id: "lifecycle", label: "Life Cycle Modifiers" },
];

// ---------------------------------------------------------------------------
//  Component
// ---------------------------------------------------------------------------

function AppShell() {
  const [activeTab, setActiveTab]   = useState<TabId>("dynasties");
  const [initConfig, setInitConfig] = useState<InitializationConfig | null>(null);
  const [lifeConfig, setLifeConfig] = useState<LifeStagesConfig | null>(null);
  const [loadError, setLoadError]   = useState<string | null>(null);
  const [apiReady, setApiReady]     = useState(false);

  // Phase 1: wait for the FastAPI sidecar to be reachable before fetching config.
  useEffect(() => {
    waitForApi(12, 800)
      .then(() => setApiReady(true))
      .catch((err: Error) => {
        setLoadError(
          `Could not reach the API server. Is the backend running?\n\n${err.message}`
        );
      });
  }, []);

  // Phase 2: once the API is confirmed up, load both config files.
  useEffect(() => {
    if (!apiReady) return;

    Promise.all([fetchInitializationConfig(), fetchLifeStagesConfig()])
      .then(([init, life]) => {
        setInitConfig(init);
        setLifeConfig(life);
      })
      .catch((err: Error) => {
        setLoadError(`Failed to load configuration: ${err.message}`);
      });
  }, [apiReady]);

  if (loadError) {
    return (
      <div className="app-shell">
        <div className="tab-content">
          <div className="msg msg-error" style={{ whiteSpace: "pre-wrap" }}>
            {loadError}
          </div>
        </div>
      </div>
    );
  }

  if (!initConfig || !lifeConfig) {
    return (
      <div className="app-shell">
        <div
          className="tab-content"
          style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}
        >
          <span className="spinner" />
          {apiReady ? "Loading configuration..." : "Waiting for API server to start..."}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>CK3 Character History Generator</h1>
      </header>

      <nav className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn${activeTab === tab.id ? " active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="tab-content">
        {activeTab === "dynasties" && (
          <DynastySettings config={initConfig} onConfigChange={setInitConfig} />
        )}
        {activeTab === "trees" && <DynastyTrees />}
        {activeTab === "events" && (
          <NegativeEvents config={initConfig} onConfigChange={setInitConfig} />
        )}
        {activeTab === "lifecycle" && (
          <LifeCycleModifiers config={lifeConfig} onConfigChange={setLifeConfig} />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  );
}