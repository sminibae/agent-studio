import type { components } from "@/lib/api/generated/schema";
import { createApiClient } from "@/lib/api/client";

export type LiveHealth = components["schemas"]["LiveResponse"];
export type CurrentUser = components["schemas"]["CurrentUserResponse"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isLiveHealth(value: unknown): value is LiveHealth {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    candidate.service === "agent-studio-api" &&
    typeof candidate.version === "string"
  );
}

export async function fetchLiveHealth(
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<LiveHealth> {
  const { data, response } = await createApiClient(fetcher).GET("/api/v1/health/live", {
    signal,
  });

  if (!response.ok) {
    throw new ApiError(`Health check failed with HTTP ${response.status}.`, response.status);
  }
  if (!isLiveHealth(data)) {
    throw new ApiError("Health check returned an unexpected response.");
  }
  return data;
}

export async function fetchCurrentUser(
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<CurrentUser> {
  const { data, response } = await createApiClient(fetcher).GET("/api/v1/me", { signal });

  if (!response.ok) {
    throw new ApiError(`User lookup failed with HTTP ${response.status}.`, response.status);
  }
  if (!data) {
    throw new ApiError("User lookup returned an unexpected response.");
  }
  return data;
}
