import { test, expect } from '@playwright/test';

test('create project and view details', async ({ page }) => {
  await page.goto('http://localhost:3501');
  await page.fill('input[type="text"]', 'e2euser');
  await page.fill('input[type="password"]', 'e2epass123');
  await page.click('button:has-text("Login")');
  await expect(page.locator('text=Projects')).toBeVisible();

  await page.click('button:has-text("New Project")');
  await page.fill('input[placeholder="Name"]', 'E2E Project 2');
  await page.fill('input[placeholder="App URL"]', 'http://localhost:3000');
  await page.fill('input[placeholder="GitHub Owner"]', 'test');
  await page.fill('input[placeholder="GitHub Repo"]', 'repo');
  await page.click('button:has-text("Create")');

  await expect(page.locator('text=E2E Project 2')).toBeVisible();
  await page.click('text=E2E Project 2');
  await expect(page.locator('text=Run Execution')).toBeVisible();
});
