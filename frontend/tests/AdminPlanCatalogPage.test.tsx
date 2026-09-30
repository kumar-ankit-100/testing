import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminPlanCatalogPage } from "../src/ui/pages/AdminPlanCatalogPage";
import { usePlanCatalog } from "../src/service/usePlanCatalog";
import type { PlanVersionDto } from "../src/types/api";

vi.mock("../src/service/usePlanCatalog");

function buildVersion(overrides: Partial<PlanVersionDto>): PlanVersionDto {
  return {
    plan_version_id: "pv-1",
    plan_id: "PLAN-5G",
    plan_name: "Unlimited 5G Postpaid",
    plan_type: "POSTPAID",
    version_number: 1,
    price: "799.00",
    terms: { validity_days: 28, data_gb: 2, sms_per_day: 100 },
    published: true,
    created_at: "2026-09-01T09:00:00Z",
    published_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}

describe("AdminPlanCatalogPage", () => {
  const createDraft = vi.fn().mockResolvedValue(true);
  const publishDraft = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    vi.clearAllMocks();
    createDraft.mockResolvedValue(true);
    publishDraft.mockResolvedValue(undefined);
  });

  function renderPage(versions: PlanVersionDto[]): void {
    vi.mocked(usePlanCatalog).mockReturnValue({
      versions,
      loading: false,
      error: null,
      createDraft,
      publishDraft,
    });
    render(
      <AdminPlanCatalogPage
        planId="PLAN-5G"
        planName="Unlimited 5G Postpaid"
        planType="POSTPAID"
      />,
    );
  }

  it("lists every version with a visible published/draft badge (AC-1)", () => {
    renderPage([
      buildVersion({ plan_version_id: "pv-1", version_number: 1, published: true }),
      buildVersion({ plan_version_id: "pv-2", version_number: 2, published: false }),
    ]);

    const badges = screen.getAllByTestId("state-badge");
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent("PUBLISHED");
    expect(badges[1]).toHaveTextContent("DRAFT");
  });

  it("clicking Edit on a published version shows a blocked, inline message (AC-3)", () => {
    renderPage([buildVersion({ published: true })]);

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));

    const message = screen.getByTestId("edit-locked-message");
    expect(message).toHaveTextContent("published and immutable");
    expect(message).toHaveTextContent("Create a new draft version instead");
    expect(screen.getByLabelText("Price")).toBeDisabled();
  });

  it("prefills the draft form from the published version's fields (AC-2)", () => {
    renderPage([
      buildVersion({ published: true, price: "799.00", terms: { validity_days: 28, data_gb: 2, sms_per_day: 100 } }),
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.click(screen.getByRole("button", { name: /Create draft from/ }));

    expect(screen.getByLabelText("Monthly price")).toHaveValue("799.00");
    expect(screen.getByLabelText("Validity (days)")).toHaveValue(28);
    expect(screen.getByLabelText("Data quota / day (GB)")).toHaveValue(2);
    expect(screen.getByLabelText("SMS / day")).toHaveValue(100);
  });

  it("submitting the draft form calls createDraft with the entered fields (AC-2)", async () => {
    renderPage([]);

    fireEvent.change(screen.getByLabelText("Monthly price"), { target: { value: "549.00" } });
    fireEvent.change(screen.getByLabelText("Validity (days)"), { target: { value: "28" } });
    fireEvent.change(screen.getByLabelText("Data quota / day (GB)"), { target: { value: "2.5" } });
    fireEvent.change(screen.getByLabelText("SMS / day"), { target: { value: "100" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Create draft" }));
    });

    expect(createDraft).toHaveBeenCalledWith({
      plan_id: "PLAN-5G",
      plan_name: "Unlimited 5G Postpaid",
      plan_type: "POSTPAID",
      price: "549.00",
      terms: { validity_days: 28, data_gb: 2.5, sms_per_day: 100 },
    });
  });

  it("clicking Publish on a draft calls publishDraft, which updates the badge via refresh (AC-4)", () => {
    renderPage([buildVersion({ plan_version_id: "pv-2", published: false })]);

    fireEvent.click(screen.getByRole("button", { name: "Publish" }));

    expect(publishDraft).toHaveBeenCalledWith("pv-2");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the error message as an alert when the hook reports one", () => {
    vi.mocked(usePlanCatalog).mockReturnValue({
      versions: [],
      loading: false,
      error: "Failed to load plan versions",
      createDraft,
      publishDraft,
    });

    render(
      <AdminPlanCatalogPage
        planId="PLAN-5G"
        planName="Unlimited 5G Postpaid"
        planType="POSTPAID"
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Failed to load plan versions");
  });
});
