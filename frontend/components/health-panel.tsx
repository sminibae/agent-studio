"use client";

import { useCallback, useEffect, useState } from "react";

import {
  fetchCurrentUser,
  fetchLiveHealth,
  type CurrentUser,
  type LiveHealth,
} from "@/lib/api/workspace";

type HealthState =
  | { readonly phase: "loading" }
  | {
      readonly phase: "success";
      readonly health: LiveHealth;
      readonly user: CurrentUser;
    }
  | { readonly phase: "error"; readonly message: string };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The API could not be reached.";
}

export function HealthPanel() {
  const [state, setState] = useState<HealthState>({ phase: "loading" });
  const [requestKey, setRequestKey] = useState(0);

  const retry = useCallback(() => {
    setState({ phase: "loading" });
    setRequestKey((key) => key + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([fetchLiveHealth(controller.signal), fetchCurrentUser(controller.signal)])
      .then(([health, user]) => setState({ phase: "success", health, user }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ phase: "error", message: errorMessage(error) });
        }
      });

    return () => controller.abort();
  }, [requestKey]);

  if (state.phase === "loading") {
    return (
      <section className="status-card" aria-live="polite" aria-busy="true">
        <div className="status-icon status-icon-loading" aria-hidden="true" />
        <div>
          <p className="eyebrow">API connection</p>
          <h2>Checking workspace health…</h2>
          <p className="muted">Connecting to the local Agent Studio service.</p>
        </div>
      </section>
    );
  }

  if (state.phase === "error") {
    return (
      <section className="status-card status-card-error" role="alert">
        <div className="status-icon status-icon-error" aria-hidden="true">
          !
        </div>
        <div className="status-copy">
          <p className="eyebrow">API connection</p>
          <h2>Service unavailable</h2>
          <p className="muted">{state.message}</p>
        </div>
        <button className="secondary-button" type="button" onClick={retry}>
          Try again
        </button>
      </section>
    );
  }

  return (
    <section className="status-card status-card-success" aria-live="polite">
      <div className="status-icon status-icon-success" aria-hidden="true">
        ✓
      </div>
      <div className="status-copy">
        <p className="eyebrow">API connection</p>
        <h2>Workspace is ready</h2>
        <p className="muted">
          {state.health.service} is ready for {state.user.display_name ?? state.user.email}.
        </p>
      </div>
      <span className="version">v{state.health.version}</span>
    </section>
  );
}
