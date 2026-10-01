import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as subscriberApi from "../src/api/subscriberApi";
import { useRegistration } from "../src/service/useRegistration";

vi.mock("../src/api/subscriberApi");

describe("useRegistration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("stores the registration result on success", async () => {
    vi.mocked(subscriberApi.registerSubscriber).mockResolvedValue({
      subscriber_id: "sub-1",
      subscription_id: "subn-1",
      state: "PENDING_KYC",
    });

    const { result } = renderHook(() => useRegistration());

    await act(async () => {
      await result.current.register("9876543210", "AADHAAR-1234", "POSTPAID");
    });

    expect(result.current.result?.state).toBe("PENDING_KYC");
    expect(result.current.error).toBeNull();
  });

  it("exposes an error message on failure", async () => {
    vi.mocked(subscriberApi.registerSubscriber).mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useRegistration());

    await act(async () => {
      await result.current.register("9876543210", "AADHAAR-1234", "POSTPAID");
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.result).toBeNull();
  });
});
