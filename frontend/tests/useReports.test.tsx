import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as reportsApi from "../src/api/reportsApi";
import { useReports } from "../src/service/useReports";

vi.mock("../src/api/reportsApi");

describe("useReports", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads the dashboard on mount", async () => {
    vi.mocked(reportsApi.getAdminDashboard).mockResolvedValue({
      activation_funnel: { registered: 10, kyc_passed: 8, dealer_passed: 8, mnp_passed: 8, activated: 8 },
      plan_mix: { PREPAID: 5, POSTPAID: 3 },
      plan_mix_percentages: { PREPAID: "62.50", POSTPAID: "37.50" },
      churn: {},
      arpu_trend: {},
      metadata: { arpu_trend_is_stubbed: true, arpu_trend_note: "stubbed" },
    });

    const { result } = renderHook(() => useReports());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.dashboard?.activation_funnel.registered).toBe(10);
    expect(result.current.error).toBeNull();
  });

  it("surfaces an API error", async () => {
    vi.mocked(reportsApi.getAdminDashboard).mockRejectedValue(
      new ApiError(403, "FORBIDDEN", "Not authorized"),
    );

    const { result } = renderHook(() => useReports());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Not authorized");
    expect(result.current.dashboard).toBeNull();
  });
});
