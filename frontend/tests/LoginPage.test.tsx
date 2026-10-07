import { fireEvent, render, screen } from "@testing-library/react";
import { act } from "react";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "../src/ui/pages/LoginPage";

describe("LoginPage", () => {
  it("submits staff credentials by default", async () => {
    const onLogin = vi.fn().mockResolvedValue(true);
    render(<LoginPage onLogin={onLogin} onGoToStaffRegister={() => {}} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "admin_raj" } });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "AdminDemo!2026Synthetic" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    });

    expect(onLogin).toHaveBeenCalledWith({
      username: "admin_raj",
      password: "AdminDemo!2026Synthetic",
    });
  });

  it("submits a mobile number when subscriber mode is selected", async () => {
    const onLogin = vi.fn().mockResolvedValue(true);
    render(<LoginPage onLogin={onLogin} onGoToStaffRegister={() => {}} />);

    fireEvent.click(screen.getByLabelText("Subscriber"));
    fireEvent.change(screen.getByLabelText("Mobile number"), {
      target: { value: "9876543210" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    });

    expect(onLogin).toHaveBeenCalledWith({ mobile_number: "9876543210" });
  });

  it("shows an error message when login fails", async () => {
    const onLogin = vi.fn().mockResolvedValue(false);
    render(<LoginPage onLogin={onLogin} onGoToStaffRegister={() => {}} />);

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "admin_raj" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    });

    expect(screen.getByRole("alert")).toHaveTextContent("Invalid credentials");
  });
});
