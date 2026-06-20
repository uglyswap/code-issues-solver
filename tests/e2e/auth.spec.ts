import { test, expect } from '@playwright/test';

test('user can register and login', async ({ page }) => {
  await page.goto('http://localhost:3501');
  await page.fill('input[type="text"]', 'e2euser');
  await page.fill('input[type="email"]', 'e2e@test.com');
  await page.fill('input[type="password"]', 'e2epass123');
  await page.click('button:has-text("Register")');
  await expect(page.locator('text=Projects')).toBeVisible({ timeout: 10000 });
});

test('user can create a project and run execution', async ({ page }) => {
  await page.goto('http://localhost:3501');
  // Login first
  await page.fill('input[type="text"]', 'e2euser');
  await page.fill('input[type="password"]', 'e2epass123');
  await page.click('button:has-text("Login")');
  await expect(page.locator('text=Projects')).toBeVisible();

  // Create project
  await page.click('button:has-text("New Project")');
  await page.fill('input[placeholder="Name"]', 'E2E Project');
  await page.fill('input[placeholder="App URL"]', 'http://localhost:3000');
  await page.fill('input[placeholder="GitHub Owner"]', 'test');
  await page.fill('input[placeholder="GitHub Repo"]', 'repo');
  await page.click('button:has-text("Create")');
  await expect(page.locator('text=E2E Project')).toBeVisible();

  // Run execution
  await page.click('text=E2E Project');
  await page.click('button:has-text("Run Execution")');
  await expect(page.locator('text=Execution')).toBeVisible();
});
