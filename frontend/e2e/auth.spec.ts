import { test, expect } from './fixtures';

test.describe('Scenario A: Authentication Workflows', () => {
  test('A.1 - A.2: Open application and register a new account', async ({ monitoredPage }) => {
    const { page, consoleErrors } = monitoredPage;
    const id = Math.floor(Math.random() * 1000000);
    const freshUser = {
      username: `fresh_user_${id}`,
      email: `fresh_${id}@example.com`,
      password: `Password123!${id}`,
      fullName: `Fresh User ${id}`
    };

    await page.goto('/');

    // Verify title and auth page elements
    await expect(page.locator('text=PRD Framework')).toBeVisible();
    await expect(page.locator('text=Local-First Automated Requirements Engineering')).toBeVisible();

    // Toggle to Register mode
    await page.click('button:has-text("Don\'t have an account? Register")');
    await expect(page.locator('button[type="submit"]')).toHaveText('Register Account');

    // Fill form
    await page.fill('input[type="text"]:near(:text("Username"))', freshUser.username);
    await page.fill('input[type="text"]:near(:text("Full Name"))', freshUser.fullName);
    await page.fill('input[type="email"]', freshUser.email);
    await page.fill('input[type="password"]', freshUser.password);

    // Submit registration
    await page.click('button[type="submit"]');

    // Should automatically log in and display Dashboard
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
    await expect(page.locator(`text=${freshUser.fullName}`)).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });

  test('A.3: Attempt registration with invalid data', async ({ monitoredPage }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    await page.click('button:has-text("Don\'t have an account? Register")');

    // Invalid email format
    await page.fill('input[type="text"]:near(:text("Username"))', 'invalid_user');
    await page.fill('input[type="email"]', 'not-an-email');
    await page.fill('input[type="password"]', 'short');

    // HTML5 validation or backend rejection
    await page.click('button[type="submit"]');
    // If HTML5 validation prevents submission, page stays on auth
    await expect(page.locator('text=Idea in. Professional PRD out.')).not.toBeVisible();
  });

  test('A.4: Attempt duplicate registration', async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    // Attempt to register with the same username/email as testUser (who was already registered by the fixture)
    await page.click('button:has-text("Don\'t have an account? Register")');
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="text"]:near(:text("Full Name"))', 'Duplicate User');
    await page.fill('input[type="email"]', testUser.email);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');

    // Should display error message
    const errorAlert = page.locator('.bg-rose-50');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText(/already exists|already registered/i);
  });

  test('A.5: Login with valid credentials', async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    // In login mode
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
  });

  test('A.6: Login with invalid credentials', async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', 'WrongPassword!999');
    await page.click('button[type="submit"]');

    const errorAlert = page.locator('.bg-rose-50');
    await expect(errorAlert).toBeVisible();
    await expect(errorAlert).toContainText(/incorrect username or password/i);
  });

  test('A.7 - A.8: Refresh browser after login and verify session persistence', async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible();

    // Reload page
    await page.reload();

    // Session should persist without showing login form
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 10000 });
  });

  test('A.9 - A.10: Logout and verify protected routes cannot be accessed', async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');

    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible();

    // Click logout button (title="Sign out")
    await page.click('button[title="Sign out"]');

    // Should return to login page
    await expect(page.locator('button[type="submit"]')).toHaveText('Sign In Locally');
    await expect(page.locator('text=Idea in. Professional PRD out.')).not.toBeVisible();

    // Reloading after logout still shows login
    await page.reload();
    await expect(page.locator('button[type="submit"]')).toHaveText('Sign In Locally');
  });
});
