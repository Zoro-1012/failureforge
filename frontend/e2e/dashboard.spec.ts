import { test, expect } from "@playwright/test";

// These tests drive the real dashboard against a running stack. Boot it with
// scripts/e2e-ui.sh, which uses the stub diagnosis provider so the diagnosis
// result is deterministic (✓ Correct).

test("dashboard renders core UI", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // Stat cards.
  await expect(page.getByText("Total incidents")).toBeVisible();
  await expect(page.getByText("Overall accuracy")).toBeVisible();

  // All four scenario buttons.
  for (const label of ["Redis Outage", "Database Deadlock", "Memory Leak", "Slow Database"]) {
    await expect(page.getByRole("button", { name: label })).toBeVisible();
  }
});

test("run scenario → diagnose → correct result", async ({ page }) => {
  await page.goto("/");

  // Launch a scenario (takes ~15s end to end).
  await page.getByRole("button", { name: "Redis Outage" }).click();

  const success = page.getByText(/Captured incident_\d+/);
  await expect(success).toBeVisible({ timeout: 60_000 });

  const text = (await success.textContent()) ?? "";
  const incidentId = text.match(/incident_\d+/)?.[0];
  expect(incidentId).toBeTruthy();

  // Open the incident.
  await page.getByRole("link", { name: incidentId! }).first().click();
  await expect(page.getByRole("heading", { name: incidentId! })).toBeVisible();

  // Logs + metrics rendered.
  await expect(page.getByRole("heading", { name: /Logs/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Metrics/ })).toBeVisible();

  // Run AI diagnosis and assert the evaluation result.
  await page.getByRole("button", { name: /Run AI diagnosis/ }).click();
  await expect(page.getByText("✓ Correct")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("90%")).toBeVisible(); // stub confidence
});
