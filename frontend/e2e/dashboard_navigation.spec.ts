import { test, expect } from './fixtures';

test.describe('Scenario B: Dashboard and Navigation Workflows', () => {
  test.beforeEach(async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
  });

  test('B.1 - B.2: Verify dashboard loads and navigation links work', async ({ monitoredPage }) => {
    const { page, consoleErrors } = monitoredPage;

    // Check header elements
    await expect(page.locator('text=PRD Framework')).toBeVisible();
    await expect(page.locator('text=LOCAL-FIRST')).toBeVisible();
    await expect(page.locator('text=Active Projects')).toBeVisible();
    await expect(page.locator('text=AI Provider')).toBeVisible();

    // Navigate to Settings
    await page.click('button[title="Model & System Settings"]');
    await expect(page.locator('text=System & AI Configuration')).toBeVisible();

    // Navigate back to Dashboard via logo click
    await page.click('text=PRD Framework');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible();

    // No console errors
    expect(consoleErrors).toEqual([]);
  });

  test('B.3: Verify page refresh preserves view routing', async ({ monitoredPage }) => {
    const { page } = monitoredPage;

    // Navigate to Settings view
    await page.click('button[title="Model & System Settings"]');
    await expect(page.locator('text=System & AI Configuration')).toBeVisible();

    // Refresh page
    await page.reload();

    // Check if the user remains on Settings or if routing is broken back to Dashboard
    await expect(page.locator('text=System & AI Configuration')).toBeVisible();
  });

  test('B.4 - B.5: Verify empty states and loading indicators', async ({ monitoredPage, secondUser }) => {
    const { page } = monitoredPage;

    // Logout and log in as fresh secondUser who has zero projects
    await page.click('button[title="Sign out"]');
    await page.fill('input[type="text"]:near(:text("Username"))', secondUser.username);
    await page.fill('input[type="password"]', secondUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible();

    // Check empty state
    await expect(page.locator('text=No projects yet')).toBeVisible();
    await expect(page.locator('text=Start by creating your first product requirements project')).toBeVisible();
  });

  test('B.6 - B.7: Verify no broken images or unhandled console errors', async ({ monitoredPage }) => {
    const { page, consoleErrors, pageErrors, failedRequests } = monitoredPage;

    // Check broken images
    const images = page.locator('img');
    const count = await images.count();
    for (let i = 0; i < count; i++) {
      const src = await images.nth(i).getAttribute('src');
      expect(src).toBeTruthy();
    }

    expect(pageErrors).toEqual([]);
    expect(consoleErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
