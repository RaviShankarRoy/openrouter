import { expect, test } from "@playwright/test";

test("landing page renders headline and CTA", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("models marketplace renders the search filter", async ({ page }) => {
  await page.goto("/models");
  await expect(page.getByPlaceholder(/search models/i)).toBeVisible();
});
