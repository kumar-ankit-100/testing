import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RouteGuard } from "../src/ui/components/RouteGuard";

describe("RouteGuard", () => {
  it("renders the fallback when not authenticated", () => {
    render(
      <RouteGuard isAuthenticated={false} role={null} fallback={<p>Please log in</p>}>
        <p>Protected content</p>
      </RouteGuard>,
    );

    expect(screen.getByText("Please log in")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated and no role restriction is given", () => {
    render(
      <RouteGuard isAuthenticated={true} role="subscriber" fallback={<p>Please log in</p>}>
        <p>Protected content</p>
      </RouteGuard>,
    );

    expect(screen.getByText("Protected content")).toBeInTheDocument();
  });

  it("renders the fallback when authenticated but the role is not allowed", () => {
    render(
      <RouteGuard
        isAuthenticated={true}
        role="subscriber"
        allowedRoles={["admin"]}
        fallback={<p>Not authorized</p>}
      >
        <p>Admin-only content</p>
      </RouteGuard>,
    );

    expect(screen.getByText("Not authorized")).toBeInTheDocument();
    expect(screen.queryByText("Admin-only content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated and the role is allowed", () => {
    render(
      <RouteGuard
        isAuthenticated={true}
        role="admin"
        allowedRoles={["admin"]}
        fallback={<p>Not authorized</p>}
      >
        <p>Admin-only content</p>
      </RouteGuard>,
    );

    expect(screen.getByText("Admin-only content")).toBeInTheDocument();
  });
});
