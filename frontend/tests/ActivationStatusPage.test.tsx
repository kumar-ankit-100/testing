import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as planApi from "../src/api/planApi";
import * as subscriberApi from "../src/api/subscriberApi";
import { setStoredSubscriptionId } from "../src/config/authStorage";
import { ActivationStatusPage } from "../src/ui/pages/ActivationStatusPage";

vi.mock("../src/api/subscriberApi");
vi.mock("../src/api/planApi");

describe("ActivationStatusPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setStoredSubscriptionId("subn-1");
    vi.mocked(planApi.listPublishedPlans).mockResolvedValue([]);
  });

  it("goes straight to the management panel for an already-ACTIVE subscriber, without the dealer-code form (regression: a page refresh previously reset to PENDING_KYC and re-submitting then raised ALREADY_ACTIVE)", async () => {
    vi.mocked(subscriberApi.getSubscriptionDetail).mockResolvedValue({
      subscription_id: "subn-1",
      subscriber_id: "sub-1",
      mobile_number: "9876543210",
      plan_type: "POSTPAID",
      state: "ACTIVE",
      dealer_code: "DLR-BLR-001",
      created_at: "2026-01-01T00:00:00Z",
      activated_at: "2026-01-02T00:00:00Z",
      current_plan: null,
    });

    render(<ActivationStatusPage subscriberId="sub-1" />);

    await waitFor(() => {
      expect(screen.getByTestId("subscription-management-panel")).toBeInTheDocument();
    });

    expect(screen.queryByLabelText("Dealer code")).not.toBeInTheDocument();
    expect(subscriberApi.activateSubscriber).not.toHaveBeenCalled();
  });

  it("shows the dealer-code form for a subscriber still in PENDING_KYC", async () => {
    vi.mocked(subscriberApi.getSubscriptionDetail).mockResolvedValue({
      subscription_id: "subn-2",
      subscriber_id: "sub-2",
      mobile_number: "9876543211",
      plan_type: "POSTPAID",
      state: "PENDING_KYC",
      dealer_code: null,
      created_at: "2026-01-01T00:00:00Z",
      activated_at: null,
      current_plan: null,
    });

    render(<ActivationStatusPage subscriberId="sub-2" />);

    await waitFor(() => {
      expect(screen.getByLabelText("Dealer code")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("subscription-management-panel")).not.toBeInTheDocument();
  });
});
