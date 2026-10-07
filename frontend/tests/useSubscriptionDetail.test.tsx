import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as subscriberApi from "../src/api/subscriberApi";
import { useSubscriptionDetail } from "../src/service/useSubscriptionDetail";

vi.mock("../src/api/subscriberApi");

const _DETAIL = {
  subscription_id: "subn-1",
  subscriber_id: "sub-1",
  mobile_number: "9876543210",
  plan_type: "POSTPAID" as const,
  state: "ACTIVE" as const,
  dealer_code: "DLR-BLR-001",
  created_at: "2026-01-01T00:00:00Z",
  activated_at: "2026-01-02T00:00:00Z",
  current_plan: null,
};

describe("useSubscriptionDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the subscriber's own subscription on mount", async () => {
    vi.mocked(subscriberApi.getSubscriptionDetail).mockResolvedValue(_DETAIL);

    const { result } = renderHook(() => useSubscriptionDetail("sub-1"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.detail?.subscription_id).toBe("subn-1");
    expect(result.current.lastUpdatedAt).not.toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("surfaces an API error", async () => {
    vi.mocked(subscriberApi.getSubscriptionDetail).mockRejectedValue(
      new ApiError(403, "FORBIDDEN", "Not authorized"),
    );

    const { result } = renderHook(() => useSubscriptionDetail("sub-1"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Not authorized");
    expect(result.current.detail).toBeNull();
  });

  it("exposes a manual refresh that re-fetches immediately", async () => {
    vi.mocked(subscriberApi.getSubscriptionDetail).mockResolvedValue(_DETAIL);

    const { result } = renderHook(() => useSubscriptionDetail("sub-1"));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(subscriberApi.getSubscriptionDetail).toHaveBeenCalledTimes(2);
    });
  });
});
