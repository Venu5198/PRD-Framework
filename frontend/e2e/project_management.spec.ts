import { test, expect } from './fixtures';

test.describe('Scenario C: Project Management Workflows', () => {
  test.beforeEach(async ({ monitoredPage, testUser }) => {
    const { page } = monitoredPage;
    await page.goto('/');
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
  });

  test('C.1 - C.2: Create a project and open it', async ({ monitoredPage }) => {
    const { page, consoleErrors } = monitoredPage;
    const projectTitle = `Test Project ${Date.now()}`;

    // Click "New PRD Project" button
    await page.click('button:has-text("New PRD Project")');
    await expect(page.locator('text=Create New PRD Project')).toBeVisible();

    // Fill project form
    await page.fill('input[placeholder*="NextGen"]', projectTitle);
    await page.fill('textarea[placeholder*="Optional context"]', 'Comprehensive requirements for microservice platform.');
    await page.click('button[type="submit"]:has-text("Create & Proceed")');

    // Should navigate into the ProjectView
    await expect(page.locator(`h1:has-text("${projectTitle}")`)).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=1. Submit Idea')).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });

  test('C.7: Cross-user project access rejection', async ({ monitoredPage, testUser, secondUser, request }) => {
    const { page } = monitoredPage;

    // Create a project owned by testUser via API
    const loginRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: testUser.username, password: testUser.password }
    });
    const tokenData = await loginRes.json();
    const testUserToken = tokenData.access_token;

    const projRes = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${testUserToken}` },
      data: {
        title: 'Secret User A Project',
        description: 'Private confidential specifications',
        target_domain: 'General Software'
      }
    });
    const project = await projRes.json();
    const projectId = project.id;

    // Log out testUser and log in as secondUser
    await page.click('button[title="Sign out"]');
    await page.fill('input[type="text"]:near(:text("Username"))', secondUser.username);
    await page.fill('input[type="password"]', secondUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible();

    // Verify secondUser does NOT see testUser's project in their dashboard grid
    await expect(page.locator('text=Secret User A Project')).not.toBeVisible();

    // Attempt direct API access to testUser's project using secondUser's token
    const loginSecRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: secondUser.username, password: secondUser.password }
    });
    const secTokenData = await loginSecRes.json();
    const secToken = secTokenData.access_token;

    const attackRes = await request.get(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${secToken}` }
    });

    expect(attackRes.status()).toBe(404);
  });

  test('C.3 - C.4: Project PATCH and DELETE verification (BUG-API-001)', async ({ request, testUser }) => {
    // Obtain auth token
    const loginRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: testUser.username, password: testUser.password }
    });
    const token = (await loginRes.json()).access_token;

    // Create project
    const createRes = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: 'Initial Project Name', description: 'Initial description' }
    });
    const project = await createRes.json();
    const projectId = project.id;

    // 1. PATCH project
    const patchRes = await request.patch(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: 'Updated Project Name via PATCH', description: 'Updated description' }
    });
    expect(patchRes.status()).toBe(200);
    const patchedData = await patchRes.json();
    expect(patchedData.title).toBe('Updated Project Name via PATCH');
    expect(patchedData.description).toBe('Updated description');

    // 2. DELETE project
    const delRes = await request.delete(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(delRes.status()).toBe(200);

    // 3. Confirm deletion
    const getRes = await request.get(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    expect(getRes.status()).toBe(404);
  });
});

