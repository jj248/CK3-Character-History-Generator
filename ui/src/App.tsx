import { useEffect, useState } from "react";
import {
  fetchInitializationConfig,
  fetchLifeStagesConfig,
  InitializationConfig,
  LifeStagesConfig,
} from "./api";
import DynastySettings from "./components/DynastySettings";
import NegativeEvents from "./components/NegativeEvents";
import DynastyTrees from "./components/DynastyTrees";
import LifeCycleModifiers from "./components/LifeCycleModifiers";

type TabId = "dynasties" | "trees" | "events" | "lifecycle";

const TABS: { id: TabId; label: string }[] = [
  { id: "dynasties", label: "Dynasty Settings" },
  { id: "trees",     label: "Dynasty Trees" },
  { id: "events",    label: "Negative Events" },
  { id: "lifecycle", label: "Life Cycle Modifiers" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dynasties");
  const [initConfig, setInitConfig] = useState<InitializationConfig | null>(null);
  const [lifeConfig, setLifeConfig] = useState<LifeStagesConfig | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchInitializationConfig(), fetchLifeStagesConfig()])
      .then(([init, life]) => {
        setInitConfig(init);
        setLifeConfig(life);
      })
      .catch((err: Error) => {
        setLoadError(`Failed to load configuration: ${err.message}`);
      });
  }, []);

  if (loadError) {
    return (
      <div className="app-shell">
        <div className="tab-content">
          <div className="msg msg-error">{loadError}</div>
        </div>
      </div>
    );
  }

  if (!initConfig || !lifeConfig) {
    return (
      <div className="app-shell">
        <div className="tab-content" style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span className="spinner" />
          Loading configuration...
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