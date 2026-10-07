import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as lifecycleApi from "../src/api/lifecycleApi";
import { useLifecycle } from "../src/service/useLifecycle";

vi.mock("../src/api/lifecycleApi");

describe("useLifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("suspends an ACTIVE subscription", async () => {
    vi.mocked(lifecycleApi.suspendSubscription).mockResolvedValue({
      subscription_id: "subn-1",
      state: "SUSPENDED",
    });

    const { result } = renderHook(() => useLifecycle("ACTIVE"));

    await act(async () => {
      await result.current.suspend("subn-1");
    });

    expect(result.current.state).toBe("SUSPENDED");
    expect(result.current.error).toBeNull();
  });

  it("resumes a SUSPENDED subscription", async () => {
    vi.mocked(lifecycleApi.resumeSubscription).mockResolvedValue({
      subscription_id: "subn-1",
      state: "ACTIVE",
    });

    const { result } = renderHook(() => useLifecycle("SUSPENDED"));

    await act(async () => {
      await result.current.resume("subn-1");
    });

    expect(result.current.state).toBe("ACTIVE");
  });

  it("requests port-out and stores the cooling period end date", async () => {
    vi.mocked(lifecycleApi.requestPortOut).mockResolvedValue({
      port_out_event_id: "po-1",
      subscription_id: "subn-1",
      requested_at: "2026-06-01T00:00:00Z",
      cooling_period_end_at: "2026-06-08T00:00:00Z",
      status: "PENDING",
    });

    const { result } = renderHook(() => useLifecycle("ACTIVE"));

    await act(async () => {
      await result.current.requestPortOutAction("subn-1");
    });

    expect(result.current.state).toBe("PORT_OUT_REQUESTED");
    expect(result.current.coolingPeriodEndAt).toBe("2026-06-08T00:00:00Z");
  });

  it("cancels a port-out request and clears the cooling period", async () => {
    vi.mocked(lifecycleApi.cancelPortOut).mockResolvedValue({
      subscription_id: "subn-1",
      state: "ACTIVE",
    });

    const { result } = renderHook(() => useLifecycle("PORT_OUT_REQUESTED"));

    await act(async () => {
      await result.current.cancelPortOutAction("subn-1");
    });

    expect(result.current.state).toBe("ACTIVE");
    expect(result.current.coolingPeriodEndAt).toBeNull();
  });

  it("surfaces an API error without changing state", async () => {
    vi.mocked(lifecycleApi.suspendSubscription).mockRejectedValue(
      new ApiError(409, "INVALID_STATE_TRANSITION", "Not currently ACTIVE"),
    );

    const { result } = renderHook(() => useLifecycle("PENDING_KYC"));

    await act(async () => {
      await result.current.suspend("subn-1");
    });

    expect(result.current.error).toBe("Not currently ACTIVE");
    expect(result.current.state).toBe("PENDING_KYC");
  });
});
