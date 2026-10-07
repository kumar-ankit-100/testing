import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as planApi from "../src/api/planApi";
import { usePublishedPlans } from "../src/service/usePublishedPlans";

vi.mock("../src/api/planApi");

describe("usePublishedPlans", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the published catalog on mount", async () => {
    vi.mocked(planApi.listPublishedPlans).mockResolvedValue([
      {
        plan_version_id: "pv-1",
        plan_id: "PLAN-5G",
        plan_name: "Unlimited 5G Postpaid",
        plan_type: "POSTPAID",
        version_number: 1,
        price: "799.00",
        terms: { data_gb: 100, sms_per_day: 100, validity_days: 30 },
        published: true,
        created_at: "2026-01-01T00:00:00Z",
        published_at: "2026-01-01T00:00:00Z",
      },
    ]);

    const { result } = renderHook(() => usePublishedPlans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.plans).toHaveLength(1);
    expect(result.current.plans[0]?.plan_id).toBe("PLAN-5G");
    expect(result.current.error).toBeNull();
  });

  it("surfaces an API error", async () => {
    vi.mocked(planApi.listPublishedPlans).mockRejectedValue(
      new ApiError(401, "UNAUTHENTICATED", "Missing bearer token"),
    );

    const { result } = renderHook(() => usePublishedPlans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Missing bearer token");
    expect(result.current.plans).toEqual([]);
  });
});
