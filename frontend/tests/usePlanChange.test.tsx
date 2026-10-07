import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as planChangeApi from "../src/api/planChangeApi";
import { usePlanChange } from "../src/service/usePlanChange";

vi.mock("../src/api/planChangeApi");

describe("usePlanChange", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("previews a pro-rata amount without committing", async () => {
    vi.mocked(planChangeApi.previewPlanChange).mockResolvedValue({
      pro_rata_amount: "42.35",
    });

    const { result } = renderHook(() => usePlanChange());

    await act(async () => {
      await result.current.preview("subn-1", "pv-2");
    });

    expect(result.current.previewAmount).toBe("42.35");
    expect(result.current.committedBillingRecordId).toBeNull();
  });

  it("commits a plan change and stores the billing record id", async () => {
    vi.mocked(planChangeApi.commitPlanChange).mockResolvedValue({
      billing_record_id: "bill-1",
      subscription_id: "subn-1",
      from_plan_version_id: "pv-1",
      to_plan_version_id: "pv-2",
      pro_rata_amount: "42.35",
      billing_period_start: "2026-06-01",
      billing_period_end: "2026-06-30",
    });

    const { result } = renderHook(() => usePlanChange());

    await act(async () => {
      await result.current.commit("subn-1", "pv-2");
    });

    expect(result.current.committedBillingRecordId).toBe("bill-1");
  });

  it("surfaces an API error on preview", async () => {
    vi.mocked(planChangeApi.previewPlanChange).mockRejectedValue(
      new ApiError(422, "MIN_TENURE_NOT_MET", "Minimum tenure not met"),
    );

    const { result } = renderHook(() => usePlanChange());

    await act(async () => {
      await result.current.preview("subn-1", "pv-2");
    });

    expect(result.current.error).toBe("Minimum tenure not met");
    expect(result.current.previewAmount).toBeNull();
  });

  it("reset clears preview, commit, and error state", async () => {
    vi.mocked(planChangeApi.previewPlanChange).mockResolvedValue({
      pro_rata_amount: "42.35",
    });
    const { result } = renderHook(() => usePlanChange());
    await act(async () => {
      await result.current.preview("subn-1", "pv-2");
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.previewAmount).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
