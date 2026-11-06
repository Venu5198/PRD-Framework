import { test, expect } from './fixtures';

const VIEWPORTS = [
  { name: 'Desktop', width: 1440, height: 900 },
  { name: 'Laptop', width: 1280, height: 800 },
  { name: 'Tablet', width: 768, height: 1024 },
  { name: 'Mobile', width: 390, height: 844 },
];

test.describe('Scenario I: Responsive UI Viewport Audits', () => {
  for (const vp of VIEWPORTS) {
    test(`I.1 - I.7: Responsive check on ${vp.name} (${vp.width}x${vp.height})`, async ({ monitoredPage, testUser }) => {
      const { page, consoleErrors, pageErrors } = monitoredPage;

      // Set viewport
      await page.setViewportSize({ width: vp.width, height: vp.height });

      // 1. Auth Page check
      await page.goto('/');
      await expect(page.locator('text=PRD Framework')).toBeVisible();

      // Verify no horizontal scrolling on body
      const scrollWidthAuth = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidthAuth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidthAuth).toBeLessThanOrEqual(clientWidthAuth + 2);

      // Login
      await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
      await page.fill('input[type="password"]', testUser.password);
      await page.click('button[type="submit"]');

      // 2. Dashboard View check
      await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });

      // Verify no horizontal scrolling on dashboard
      const scrollWidthDash = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidthDash = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidthDash).toBeLessThanOrEqual(clientWidthDash + 2);

      // Verify buttons are accessible and clickable
      const newProjBtn = page.locator('button:has-text("New PRD Project")');
      await expect(newProjBtn).toBeVisible();
      await newProjBtn.click();

      // Verify modal fits within viewport
      const modal = page.locator('.fixed .max-w-lg');
      await expect(modal).toBeVisible();
      const modalBox = await modal.boundingBox();
      expect(modalBox).not.toBeNull();
      if (modalBox) {
        expect(modalBox.x).toBeGreaterThanOrEqual(0);
        expect(modalBox.x + modalBox.width).toBeLessThanOrEqual(vp.width + 10);
      }

      // Close modal
      await page.click('button:has-text("Cancel")');

      // 3. Settings View check
      await page.click('button[title="Model & System Settings"]');
      await expect(page.locator('text=System & AI Configuration')).toBeVisible();

      const scrollWidthSettings = await page.evaluate(() => document.documentElement.scrollWidth);
      const clientWidthSettings = await page.evaluate(() => document.documentElement.clientWidth);
      expect(scrollWidthSettings).toBeLessThanOrEqual(clientWidthSettings + 2);

      expect(pageErrors).toEqual([]);
      expect(consoleErrors).toEqual([]);
    });
  }
});

