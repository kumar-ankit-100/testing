/**
 * E2E spec for the admin plan catalog management UI (E3-S4).
 *
 * Requires both dev servers running per init.sh (backend on :8000,
 * frontend on :5173) and an admin bearer token available to the page —
 * not wired up yet, since no login-API story exists in this project to
 * mint one (see subscriber_schemas.py's module docstring on the backend
 * for the same documented gap). This spec is written to the project's
 * Playwright conventions (role/label selectors, no CSS/XPath, no
 * arbitrary waits) so it is ready to run once that auth wiring lands;
 * it has not been executed against live servers in this session.
 */

import { expect, test } from "@playwright/test";

test.describe("Admin plan catalog management", () => {
  test("lists plan versions with a visible published/draft badge (AC-1)", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Plan Catalog" })).toBeVisible();
    await expect(page.getByText("PUBLISHED").first()).toBeVisible();
  });

  test("creating a new draft from the form shows it in the version list (AC-2)", async ({
    page,
  }) => {
    await page.goto("/");

    await page.getByLabel("Monthly price").fill("549.00");
    await page.getByLabel("Validity (days)").fill("28");
    await page.getByLabel("Data quota / day (GB)").fill("2.5");
    await page.getByLabel("SMS / day").fill("100");
    await page.getByRole("button", { name: "Create draft" }).click();

    await expect(page.getByText("DRAFT").first()).toBeVisible();
  });

  test("editing a published version is blocked with an inline message (AC-3)", async ({
    page,
  }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Edit" }).first().click();

    await expect(page.getByText(/published and immutable/)).toBeVisible();
    await expect(page.getByText(/create a new draft version instead/i)).toBeVisible();
    await expect(page.getByLabel("Price")).toBeDisabled();
  });

  test("publishing a draft updates its badge without a full page reload (AC-4)", async ({
    page,
  }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Publish" }).first().click();

    await expect(page.getByRole("alert")).not.toBeVisible();
  });
});
