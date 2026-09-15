import createClient from "openapi-fetch";

import type { paths } from "@/lib/api/generated/schema";

export function createApiClient(fetcher: typeof fetch = fetch) {
  const baseUrl = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  return createClient<paths>({ baseUrl, fetch: fetcher });
}
