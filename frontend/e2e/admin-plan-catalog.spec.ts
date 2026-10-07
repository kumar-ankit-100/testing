/**
 * E2E spec for the admin plan catalog management UI (E3-S4).
 *
 * Logs in as the seeded admin demo user via the real login endpoint
 * (E1-S6) before each test — this previously had no way to mint a
 * token and was never executed; that gap is closed now that
 * POST /api/auth/login exists. Requires both dev servers running per
 * init.sh (backend on :8000, frontend on :5173).
 *
 * Written to this project's Playwright conventions: role/label
 * selectors only, no CSS/XPath, no arbitrary waits (expect's built-in
 * polling handles timing).
 */

import { expect, test } from "@playwright/test";

test.describe("Admin plan catalog management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.getByLabel("Username").fill("admin_raj");
    await page.getByLabel("Password").fill("AdminDemo!2026Synthetic");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("heading", { name: "Plan Catalog" })).toBeVisible();
  });

  test("lists plan versions with a working admin tab layout (AC-1)", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Plan Catalog" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reports" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Plan Catalog" })).toHaveScreenshot(
      "admin-plan-catalog-heading.png",
    );
  });

  test("creating a new draft from the form shows it in the version list (AC-2)", async ({
    page,
  }) => {
    await page.getByLabel("Monthly price").fill("549.00");
    await page.getByLabel("Validity (days)").fill("28");
    await page.getByLabel("Data quota / day (GB)").fill("2.5");
    await page.getByLabel("SMS / day").fill("100");
    await page.getByRole("button", { name: "Create draft" }).click();

    await expect(page.getByText("DRAFT").first()).toBeVisible();
  });

  test("navigating to the Reports tab shows the dashboard (AC-10)", async ({ page }) => {
    await page.getByRole("button", { name: "Reports" }).click();

    await expect(page.getByRole("heading", { name: "Reporting Dashboard" })).toBeVisible();
    await expect(page.getByText("Activation funnel")).toBeVisible();
  });

  test("the subscriber-facing login page renders responsively at mobile width (AC-4)", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Log out" }).click();
    await page.setViewportSize({ width: 375, height: 812 });

    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
  });
});
