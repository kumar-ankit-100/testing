import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as csrApi from "../src/api/csrApi";
import { useCsrOverride } from "../src/service/useCsrOverride";

vi.mock("../src/api/csrApi");

describe("useCsrOverride", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("overrides a rejected activation", async () => {
    vi.mocked(csrApi.overrideActivation).mockResolvedValue({
      subscriber_id: "sub-1",
      state: "ACTIVE",
    });

    const { result } = renderHook(() => useCsrOverride());

    await act(async () => {
      await result.current.overrideActivationAction(
        "sub-1",
        "DEALER-FAIL",
        "MANUAL_KYC_VERIFIED",
        "DEALER_INVALID",
      );
    });

    expect(result.current.result).toContain("ACTIVE");
    expect(result.current.error).toBeNull();
  });

  it("overrides a rejected plan change", async () => {
    vi.mocked(csrApi.overridePlanChange).mockResolvedValue({
      billing_record_id: "bill-1",
      subscription_id: "subn-1",
      pro_rata_amount: "42.35",
    });

    const { result } = renderHook(() => useCsrOverride());

    await act(async () => {
      await result.current.overridePlanChangeAction(
        "subn-1",
        "pv-2",
        "GOODWILL_EXCEPTION",
        "MIN_TENURE_NOT_MET",
      );
    });

    expect(result.current.result).toContain("bill-1");
  });

  it("surfaces a 403 for a non-CSR caller", async () => {
    vi.mocked(csrApi.overrideActivation).mockRejectedValue(
      new ApiError(403, "FORBIDDEN", "Role admin is not permitted"),
    );

    const { result } = renderHook(() => useCsrOverride());

    await act(async () => {
      await result.current.overrideActivationAction("sub-1", "DLR-BLR-001", "x", "y");
    });

    expect(result.current.error).toBe("Role admin is not permitted");
  });
});
