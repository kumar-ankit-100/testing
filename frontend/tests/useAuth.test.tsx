import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../src/api/authApi";
import { clearStoredSession } from "../src/config/authStorage";
import { useAuth } from "../src/service/useAuth";

vi.mock("../src/api/authApi");

describe("useAuth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearStoredSession();
  });

  afterEach(() => {
    clearStoredSession();
  });

  it("starts unauthenticated when no session is stored", () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.role).toBeNull();
  });

  it("login stores the session and updates state on success", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token-abc",
      role: "admin",
      subscriber_id: null,
      expires_in: 3600,
    });

    const { result } = renderHook(() => useAuth());

    let succeeded = false;
    await act(async () => {
      succeeded = await result.current.login({ username: "admin_raj", password: "x" });
    });

    expect(succeeded).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.role).toBe("admin");
  });

  it("login returns false and leaves state unauthenticated on failure", async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error("401"));

    const { result } = renderHook(() => useAuth());

    let succeeded = true;
    await act(async () => {
      succeeded = await result.current.login({ username: "admin_raj", password: "wrong" });
    });

    expect(succeeded).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("logout clears the session", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token-abc",
      role: "csr",
      subscriber_id: null,
      expires_in: 3600,
    });
    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.login({ username: "csr_jane", password: "x" });
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.role).toBeNull();
  });

  it("stores and exposes a subscriber's subscriber_id after a subscriber login", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token-sub",
      role: "subscriber",
      subscriber_id: "sub-123",
      expires_in: 3600,
    });

    const { result } = renderHook(() => useAuth());
    await act(async () => {
      await result.current.login({ mobile_number: "9876543210" });
    });

    expect(result.current.subscriberId).toBe("sub-123");
  });
});
