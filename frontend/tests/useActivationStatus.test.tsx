import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as subscriberApi from "../src/api/subscriberApi";
import { useActivationStatus } from "../src/service/useActivationStatus";

vi.mock("../src/api/subscriberApi");

describe("useActivationStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets state to ACTIVE on a successful activation", async () => {
    vi.mocked(subscriberApi.activateSubscriber).mockResolvedValue({
      subscriber_id: "sub-1",
      state: "ACTIVE",
      activated_at: "2026-06-01T10:00:00Z",
    });

    const { result } = renderHook(() => useActivationStatus());

    await act(async () => {
      await result.current.activate("sub-1", "DLR-BLR-001");
    });

    expect(result.current.state).toBe("ACTIVE");
    expect(result.current.reasonCode).toBeNull();
  });

  it("exposes the reason code and message on a rejected activation", async () => {
    vi.mocked(subscriberApi.activateSubscriber).mockRejectedValue(
      new ApiError(422, "KYC_UNVERIFIED", "Activation rejected: KYC_UNVERIFIED"),
    );

    const { result } = renderHook(() => useActivationStatus());

    await act(async () => {
      await result.current.activate("sub-1", "DLR-BLR-001");
    });

    expect(result.current.state).toBeNull();
    expect(result.current.reasonCode).toBe("KYC_UNVERIFIED");
    expect(result.current.message).toContain("KYC_UNVERIFIED");
  });
});
