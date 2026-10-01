import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "../src/api/client";
import { clearStoredSession, setStoredSession } from "../src/config/authStorage";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }),
    );
  });

  afterEach(() => {
    clearStoredSession();
    vi.unstubAllGlobals();
  });

  it("does not attach an Authorization header when no token is stored", async () => {
    await apiFetch("/api/whatever");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("attaches the stored token as a Bearer Authorization header", async () => {
    setStoredSession("test-token-123", "admin", null);

    await apiFetch("/api/whatever");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token-123");
  });
});
