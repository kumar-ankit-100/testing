import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import * as lifecycleApi from "../src/api/lifecycleApi";
import { useTerminate } from "../src/service/useTerminate";

vi.mock("../src/api/lifecycleApi");

describe("useTerminate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("terminates a subscription and reports the resulting state", async () => {
    vi.mocked(lifecycleApi.terminateSubscription).mockResolvedValue({
      subscription_id: "subn-1",
      state: "TERMINATED",
    });

    const { result } = renderHook(() => useTerminate());

    await act(async () => {
      await result.current.terminate("subn-1", "FRAUD_SUSPECTED");
    });

    expect(result.current.result).toContain("TERMINATED");
    expect(result.current.error).toBeNull();
  });

  it("surfaces a 403 for a subscriber token", async () => {
    vi.mocked(lifecycleApi.terminateSubscription).mockRejectedValue(
      new ApiError(403, "FORBIDDEN", "Role subscriber may not terminate"),
    );

    const { result } = renderHook(() => useTerminate());

    await act(async () => {
      await result.current.terminate("subn-1", "FRAUD_SUSPECTED");
    });

    expect(result.current.error).toBe("Role subscriber may not terminate");
  });
});
