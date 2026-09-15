import { describe, expect, it, vi } from "vitest";

import { ApiError, fetchCurrentUser, fetchLiveHealth } from "@/lib/api/workspace";

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
    const request = fetcher.mock.calls[0]?.[0];
    expect(request).toBeInstanceOf(Request);
    expect(new URL((request as Request).url).pathname).toBe("/api/v1/health/live");
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

  it("returns the current user from the generated API contract", async () => {
    const user = {
      id: "01994ef5-20f0-7000-8000-000000000001",
      issuer: "https://development.agent-studio.local",
      subject: "local-developer",
      email: "developer@localhost",
      display_name: "Local Developer",
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(user), { status: 200 }));

    await expect(fetchCurrentUser(undefined, fetcher)).resolves.toEqual(user);
  });
});
