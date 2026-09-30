import { renderHook, waitFor } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as planApi from "../src/api/planApi";
import { usePlanCatalog } from "../src/service/usePlanCatalog";
import type { PlanVersionDto } from "../src/types/api";

vi.mock("../src/api/planApi");

const PLAN_ID = "PLAN-5G";

function buildVersion(overrides: Partial<PlanVersionDto>): PlanVersionDto {
  return {
    plan_version_id: "pv-1",
    plan_id: PLAN_ID,
    plan_name: "Unlimited 5G Postpaid",
    plan_type: "POSTPAID",
    version_number: 1,
    price: "799.00",
    terms: { validity_days: 28, data_gb: 2, sms_per_day: 100 },
    published: false,
    created_at: "2026-09-01T09:00:00Z",
    published_at: null,
    ...overrides,
  };
}

describe("usePlanCatalog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads and filters versions for the given plan_id, sorted ascending", async () => {
    vi.mocked(planApi.listPlanVersions).mockResolvedValue([
      buildVersion({ plan_version_id: "pv-2", version_number: 2 }),
      buildVersion({ plan_version_id: "pv-1", version_number: 1 }),
      buildVersion({ plan_version_id: "pv-other", plan_id: "OTHER-PLAN", version_number: 1 }),
    ]);

    const { result } = renderHook(() => usePlanCatalog(PLAN_ID));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.versions.map((v) => v.plan_version_id)).toEqual(["pv-1", "pv-2"]);
    expect(result.current.error).toBeNull();
  });

  it("sets an error message when loading fails", async () => {
    vi.mocked(planApi.listPlanVersions).mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => usePlanCatalog(PLAN_ID));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("network down");
    expect(result.current.versions).toEqual([]);
  });

  it("createDraft calls the API and refreshes the version list", async () => {
    vi.mocked(planApi.listPlanVersions).mockResolvedValue([]);
    vi.mocked(planApi.createPlanVersion).mockResolvedValue({
      plan_version_id: "pv-new",
      plan_id: PLAN_ID,
      version_number: 1,
      published: false,
    });

    const { result } = renderHook(() => usePlanCatalog(PLAN_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    vi.mocked(planApi.listPlanVersions).mockResolvedValue([
      buildVersion({ plan_version_id: "pv-new" }),
    ]);

    let success = false;
    await act(async () => {
      success = await result.current.createDraft({
        plan_id: PLAN_ID,
        plan_name: "Unlimited 5G Postpaid",
        plan_type: "POSTPAID",
        price: "799.00",
        terms: { validity_days: 28, data_gb: 2, sms_per_day: 100 },
      });
    });

    expect(success).toBe(true);
    expect(planApi.createPlanVersion).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(result.current.versions.map((v) => v.plan_version_id)).toEqual(["pv-new"]),
    );
  });

  it("publishDraft calls the API and refreshes the version list", async () => {
    const draft = buildVersion({ plan_version_id: "pv-1", published: false });
    vi.mocked(planApi.listPlanVersions).mockResolvedValue([draft]);
    vi.mocked(planApi.publishPlanVersion).mockResolvedValue({
      plan_version_id: "pv-1",
      published: true,
      published_at: "2026-09-02T10:00:00Z",
    });

    const { result } = renderHook(() => usePlanCatalog(PLAN_ID));
    await waitFor(() => expect(result.current.loading).toBe(false));

    vi.mocked(planApi.listPlanVersions).mockResolvedValue([
      buildVersion({ plan_version_id: "pv-1", published: true }),
    ]);

    await act(async () => {
      await result.current.publishDraft("pv-1");
    });

    expect(planApi.publishPlanVersion).toHaveBeenCalledWith("pv-1");
    await waitFor(() => expect(result.current.versions[0]?.published).toBe(true));
  });
});
