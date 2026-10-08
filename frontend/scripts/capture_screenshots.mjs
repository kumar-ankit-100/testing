/**
 * Captures a set of reference screenshots of the running app (login,
 * registration, activation, subscriber dashboard, admin catalog/
 * reports, CSR tools, an error state) via Playwright.
 *
 * Requires both dev servers already running:
 *   backend:  cd backend && uv run uvicorn app.api.main:app --reload --port 8000
 *   frontend: cd frontend && npm run dev
 *
 * Usage (from frontend/):
 *   node scripts/capture_screenshots.mjs
 *
 * Output: frontend/screenshots/NN-<name>.png
 */

import { chromium } from "playwright";
import path from "path";

const OUT_DIR = path.resolve("screenshots");
const BASE_URL = "http://localhost:5173";

const browser = await chromium.launch();
let n = 0;

async function shot(page, name) {
  n += 1;
  const file = `${String(n).padStart(2, "0")}-${name}.png`;
  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: true });
  console.log("saved", file);
}

async function freshPage() {
  return browser.newPage({ viewport: { width: 1280, height: 900 } });
}

async function section(name, fn) {
  const page = await freshPage();
  try {
    await fn(page);
  } catch (err) {
    console.log(`[section "${name}" error]`, err.message);
  } finally {
    await page.close();
  }
}

await section("login + staff register", async (page) => {
  // 1. Login page (staff mode, default)
  await page.goto(BASE_URL);
  await page.waitForSelector("#username");
  await shot(page, "login-staff");

  // 2. Login page (subscriber mode)
  await page.click("text=Subscriber");
  await shot(page, "login-subscriber");

  // 3. Staff register page
  await page.click("text=Staff");
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForSelector("#staff-register-username");
  await shot(page, "staff-register-form");

  // 4. Staff register success
  const username = "shot_csr_" + Date.now();
  await page.fill("#staff-register-username", username);
  await page.fill("#staff-register-password", "Str0ngPass!2026");
  await page.selectOption("#staff-register-role", "csr");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=Account created");
  await shot(page, "staff-register-success");
});

const mobile = "91" + String(Date.now()).slice(-8);

await section("subscriber register + activate + dashboard", async (page) => {
  // 5. Subscriber registration form
  await page.goto(BASE_URL);
  await page.waitForSelector("#username");
  await page.click("text=Subscriber");
  await page.fill("#mobile-number", mobile);
  await page.click('button[type="submit"]');
  await page.waitForSelector("#mobile-number");
  await shot(page, "subscriber-register-form");

  // 6. Activation form (with dealer code hint)
  await page.fill("#mobile-number", mobile);
  await page.fill("#identity-proof-ref", "AADHAAR-SHOT-TEST");
  await page.click('button:has-text("Register")');
  await page.waitForSelector("#dealer-code");
  await shot(page, "activation-dealer-code-form");

  // 7. Activation success + subscriber dashboard with plan dropdown
  await page.fill("#dealer-code", "DLR-BLR-001");
  await page.click('button:has-text("Activate")');
  await page.waitForSelector('[data-testid="activation-success"]');
  await page.waitForTimeout(1500); // let the plan dropdown's async fetch finish
  await shot(page, "subscriber-dashboard-active");

  // 8. Plan change preview (may be blocked by the minimum-tenure rule on
  // a just-activated subscription — that's a real business rule, not a
  // bug, so screenshot whatever the attempt produces either way).
  const planOptions = await page.locator("#target-plan-version-id option").count();
  if (planOptions > 1) {
    await page.selectOption("#target-plan-version-id", { index: 1 });
    await page.click('button:has-text("Preview")');
    await page.waitForTimeout(1200);
    await shot(page, "plan-change-preview");
  }
});

await section("admin plan catalog + reports", async (page) => {
  // 9. Admin plan catalog
  await page.goto(BASE_URL);
  await page.waitForSelector("#username");
  await page.fill("#username", "admin_raj");
  await page.fill("#password", "AdminDemo!2026Synthetic");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=role: admin");
  await shot(page, "admin-plan-catalog");

  // 10. Admin reports dashboard
  await page.click('button:has-text("Reports")');
  await page.waitForSelector('button:has-text("Refresh now")');
  await page.waitForTimeout(500);
  await shot(page, "admin-reports-dashboard");
});

await section("csr tools", async (page) => {
  // 11. CSR tools page
  await page.goto(BASE_URL);
  await page.waitForSelector("#username");
  await page.fill("#username", "csr_jane");
  await page.fill("#password", "CsrDemo!2026Synthetic");
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=CSR Tools");
  await shot(page, "csr-tools");
});

await section("login error state", async (page) => {
  // 12. Invalid credentials
  await page.goto(BASE_URL);
  await page.waitForSelector("#username");
  await page.fill("#username", "admin_raj");
  await page.fill("#password", "wrong-password");
  await page.click('button[type="submit"]');
  await page.waitForSelector('[role="alert"]');
  await shot(page, "login-invalid-credentials");
});

await browser.close();
console.log(`\nDone — ${n} screenshots saved to ${OUT_DIR}`);
