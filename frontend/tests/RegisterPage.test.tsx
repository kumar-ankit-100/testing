import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as subscriberApi from "../src/api/subscriberApi";
import { RegisterPage } from "../src/ui/pages/RegisterPage";

vi.mock("../src/api/subscriberApi");

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the registration form and calls onRegistered with the new subscriber_id", async () => {
    vi.mocked(subscriberApi.registerSubscriber).mockResolvedValue({
      subscriber_id: "sub-42",
      subscription_id: "subn-42",
      state: "PENDING_KYC",
    });
    const onRegistered = vi.fn();

    render(<RegisterPage onRegistered={onRegistered} />);

    fireEvent.change(screen.getByLabelText("Mobile number"), {
      target: { value: "9876543210" },
    });
    fireEvent.change(screen.getByLabelText("Identity proof reference"), {
      target: { value: "AADHAAR-1234" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Register" }));
    });

    expect(subscriberApi.registerSubscriber).toHaveBeenCalledWith({
      mobile_number: "9876543210",
      identity_proof_ref: "AADHAAR-1234",
      plan_type: "PREPAID",
    });
    expect(onRegistered).toHaveBeenCalledWith("sub-42");
  });

  it("shows an error message when registration fails", async () => {
    vi.mocked(subscriberApi.registerSubscriber).mockRejectedValue(new Error("boom"));

    render(<RegisterPage onRegistered={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Mobile number"), {
      target: { value: "9876543210" },
    });
    fireEvent.change(screen.getByLabelText("Identity proof reference"), {
      target: { value: "AADHAAR-1234" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Register" }));
    });

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
