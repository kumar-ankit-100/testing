import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "../src/api/authApi";
import { useStaffRegistration } from "../src/service/useStaffRegistration";

vi.mock("../src/api/authApi");

describe("useStaffRegistration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns the registration result on success", async () => {
    vi.mocked(authApi.registerStaff).mockResolvedValue({
      user_id: "user-1",
      username: "fresh_csr",
      role: "csr",
    });

    const { result } = renderHook(() => useStaffRegistration());

    await act(async () => {
      await result.current.register({ username: "fresh_csr", password: "Str0ngPass!2026", role: "csr" });
    });

    expect(result.current.error).toBeNull();
  });

  it("exposes an error message on failure", async () => {
    vi.mocked(authApi.registerStaff).mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useStaffRegistration());

    await act(async () => {
      await result.current.register({ username: "dup", password: "Str0ngPass!2026", role: "csr" });
    });

    expect(result.current.error).not.toBeNull();
  });
});
