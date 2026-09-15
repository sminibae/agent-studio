import { describe, expect, it, vi } from "vitest";

import { ApiError, fetchLiveHealth } from "@/lib/api/health";

describe("fetchLiveHealth", () => {
  it("requests and returns a valid live-health response", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ status: "ok", service: "agent-studio-api", version: "0.1.0" }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(fetchLiveHealth(undefined, fetcher)).resolves.toEqual({
      status: "ok",
      service: "agent-studio-api",
      version: "0.1.0",
    });
    expect(fetcher).toHaveBeenCalledWith("/api/v1/health/live", {
      headers: { Accept: "application/json" },
      signal: undefined,
    });
  });

  it("exposes an HTTP status when the service rejects the request", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 503 }));

    await expect(fetchLiveHealth(undefined, fetcher)).rejects.toEqual(
      new ApiError("Health check failed with HTTP 503.", 503),
    );
  });

  it("rejects a response that does not match the contract", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ status: "fine" }), { status: 200 }));

    await expect(fetchLiveHealth(undefined, fetcher)).rejects.toThrow(
      "Health check returned an unexpected response.",
    );
  });
});
