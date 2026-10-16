import { Component, StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles.css";

const client = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10000, refetchOnWindowFocus: true },
    mutations: { retry: false },
  },
});
class WorkspaceBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="fatal-error">
        <h1>The workspace could not render.</h1>
        <p>
          Reload to reconnect to the backend. No fictional data has been
          substituted.
        </p>
        <button onClick={() => window.location.reload()}>
          Reload workspace
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WorkspaceBoundary>
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    </WorkspaceBoundary>
  </StrictMode>,
);
