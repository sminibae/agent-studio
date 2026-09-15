export interface LiveHealth {
  readonly status: "ok";
  readonly service: "agent-studio-api";
  readonly version: string;
}

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
  const response = await fetcher("/api/v1/health/live", {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(`Health check failed with HTTP ${response.status}.`, response.status);
  }

  const payload: unknown = await response.json();
  if (!isLiveHealth(payload)) {
    throw new ApiError("Health check returned an unexpected response.");
  }

  return payload;
}
