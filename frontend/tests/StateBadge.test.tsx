import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StateBadge } from "../src/ui/components/StateBadge";

describe("StateBadge", () => {
  it("renders PUBLISHED for a published version", () => {
    render(<StateBadge published={true} />);

    const badge = screen.getByTestId("state-badge");
    expect(badge).toHaveTextContent("PUBLISHED");
    expect(badge).toHaveAttribute("data-state", "published");
  });

  it("renders DRAFT for an unpublished version", () => {
    render(<StateBadge published={false} />);

    const badge = screen.getByTestId("state-badge");
    expect(badge).toHaveTextContent("DRAFT");
    expect(badge).toHaveAttribute("data-state", "draft");
  });
});
