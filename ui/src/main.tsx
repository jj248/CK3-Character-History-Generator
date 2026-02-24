/**
 * main.tsx
 *
 * React entry point. Mounts the application with StrictMode and a top-level
 * ErrorBoundary as a last-resort safety net for errors that escape the
 * boundary in App.tsx (e.g. errors thrown during the very first render before
 * App's own boundary initialises).
 */

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);