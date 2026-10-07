import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../src/api/authApi";
import { StaffRegisterPage } from "../src/ui/pages/StaffRegisterPage";

vi.mock("../src/api/authApi");

describe("StaffRegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the registration form and calls onRegistered on success", async () => {
    vi.mocked(authApi.registerStaff).mockResolvedValue({
      user_id: "user-1",
      username: "fresh_csr",
      role: "csr",
    });
    const onRegistered = vi.fn();

    render(<StaffRegisterPage onRegistered={onRegistered} onBackToLogin={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "fresh_csr" } });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "Str0ngPass!2026" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Register" }));
    });

    expect(authApi.registerStaff).toHaveBeenCalledWith({
      username: "fresh_csr",
      password: "Str0ngPass!2026",
      role: "csr",
    });
    expect(onRegistered).toHaveBeenCalled();
    expect(screen.getByText("Account created")).toBeInTheDocument();
  });

  it("shows an error message when registration fails", async () => {
    vi.mocked(authApi.registerStaff).mockRejectedValue(new Error("Username already taken"));

    render(<StaffRegisterPage onRegistered={vi.fn()} onBackToLogin={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "dup_user" } });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "Str0ngPass!2026" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Register" }));
    });

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
