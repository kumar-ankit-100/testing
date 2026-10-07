import { act, renderHook, waitFor } from "@testing-library/react";
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

  it("re-fetches on an interval so the dashboard stays live", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(reportsApi.getAdminDashboard).mockResolvedValue({
      activation_funnel: { registered: 1, kyc_passed: 1, dealer_passed: 1, mnp_passed: 1, activated: 1 },
      plan_mix: { PREPAID: 1, POSTPAID: 0 },
      plan_mix_percentages: { PREPAID: "100.00", POSTPAID: "0.00" },
      churn: {},
      arpu_trend: {},
      metadata: { arpu_trend_is_stubbed: true, arpu_trend_note: "stubbed" },
    });

    const { result, unmount } = renderHook(() => useReports());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(reportsApi.getAdminDashboard).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(reportsApi.getAdminDashboard).toHaveBeenCalledTimes(2);

    unmount();
    vi.useRealTimers();
  });

  it("exposes a manual refresh that re-fetches immediately", async () => {
    vi.mocked(reportsApi.getAdminDashboard).mockResolvedValue({
      activation_funnel: { registered: 1, kyc_passed: 1, dealer_passed: 1, mnp_passed: 1, activated: 1 },
      plan_mix: { PREPAID: 1, POSTPAID: 0 },
      plan_mix_percentages: { PREPAID: "100.00", POSTPAID: "0.00" },
      churn: {},
      arpu_trend: {},
      metadata: { arpu_trend_is_stubbed: true, arpu_trend_note: "stubbed" },
    });

    const { result } = renderHook(() => useReports());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(result.current.lastUpdatedAt).not.toBeNull();

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(reportsApi.getAdminDashboard).toHaveBeenCalledTimes(2);
    });
  });
});
