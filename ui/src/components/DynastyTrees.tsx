import { useEffect, useState } from "react";
import { fetchImageList, imageUrl } from "../api";

export default function DynastyTrees() {
  const [images, setImages] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchImageList()
      .then(setImages)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const dynastyLabel = (filename: string) =>
    filename.replace("family_tree_", "").replace(".png", "");

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Generated Dynasty Trees</h2>
        <button className="btn btn-secondary btn-sm" onClick={load}>
          Refresh
        </button>
      </div>

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", color: "var(--text-muted)" }}>
          <span className="spinner" /> Loading images...
        </div>
      )}

      {error && <div className="msg msg-error">{error}</div>}

      {!loading && images.length === 0 && (
        <div className="msg msg-info">
          No dynasty tree images found. Run the simulation first.
        </div>
      )}

      <div className="image-grid">
        {images.map((filename) => {
          const isOpen = expanded.has(filename);
          return (
            <div key={filename} className="accordion">
              <div
                className="accordion-header"
                onClick={() => toggle(filename)}
              >
                <span style={{ color: "var(--text-label)" }}>
                  {dynastyLabel(filename)}
                </span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  {isOpen ? "collapse" : "expand"}
                </span>
              </div>
              {isOpen && (
                <div className="accordion-body">
                  <div className="dynasty-image-wrap">
                    <img
                      src={imageUrl(filename)}
                      alt={`Family tree for ${dynastyLabel(filename)}`}
                      loading="lazy"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}