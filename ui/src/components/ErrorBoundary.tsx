/**
 * ErrorBoundary.tsx
 *
 * A React class component that catches unhandled render/lifecycle errors from
 * any descendant component tree and displays a recovery UI instead of a blank
 * screen. React error boundaries must be class components — there is no
 * equivalent hook API.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <YourComponent />
 *   </ErrorBoundary>
 */

import { Component, ErrorInfo, ReactNode } from "react";

// ---------------------------------------------------------------------------
//  Types
// ---------------------------------------------------------------------------

interface Props {
  /** The component subtree to protect. */
  children: ReactNode;
  /**
   * Optional custom fallback. When omitted the default recovery UI is shown.
   * Receives the caught error so callers can render context-specific messages.
   */
  fallback?: (error: Error) => ReactNode;
}

interface State {
  error: Error | null;
}

// ---------------------------------------------------------------------------
//  Component
// ---------------------------------------------------------------------------

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log full detail in development; in production this could ship to a
    // monitoring service.
    console.error("[ErrorBoundary] Uncaught render error:", error, info.componentStack);
  }

  private handleReset = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    const { error } = this.state;
    const { children, fallback } = this.props;

    if (error !== null) {
      if (fallback) return fallback(error);

      return (
        <div className="app-shell">
          <div className="tab-content error-boundary">
            <h2>Something went wrong</h2>
            <p className="error-boundary__message">{error.message}</p>
            <p className="error-boundary__hint">
              This is an unexpected UI error. You can try recovering below, or
              restart the application if the problem persists.
            </p>
            <button className="btn btn-primary" onClick={this.handleReset}>
              Try to recover
            </button>
          </div>
        </div>
      );
    }

    return children;
  }
}