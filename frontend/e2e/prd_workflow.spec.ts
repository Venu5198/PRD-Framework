import { test, expect } from './fixtures';

test.describe('Scenarios F & G: PRD Generation, Editing, Validation and Export Workflows', () => {
  let projectId: string;
  let authToken: string;

  test.beforeEach(async ({ monitoredPage, testUser, request }) => {
    const { page } = monitoredPage;

    // Login via API to obtain token
    const loginRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: testUser.username, password: testUser.password }
    });
    const tokenData = await loginRes.json();
    authToken = tokenData.access_token;

    // Create a project
    const projRes = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: {
        title: `Workflow PRD Project ${Date.now()}`,
        description: 'Testing section editing, validation and exports',
        target_domain: 'General Software'
      }
    });
    const proj = await projRes.json();
    projectId = proj.id;

    // Submit submission and generate initial PRD via API to enable direct PRD tab inspection
    await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/submissions`, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: {
        submission_type: 'idea',
        raw_idea: 'Real-time collaborative code review platform',
        problem_statement: 'Engineers experience review delays and missing architectural context'
      }
    });

    // Generate initial PRD
    const genRes = await request.post(`http://127.0.0.1:8000/api/v1/prd/${projectId}/generate?use_mock=true`, {
      headers: { Authorization: `Bearer ${authToken}` }
    });
    expect(genRes.status()).toBe(200);

    // Login via UI
    await page.goto('/');
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
  });

  test('F.1 - F.11: Open PRD, edit section, save, verify persistence and versioning', async ({ monitoredPage }) => {
    const { page } = monitoredPage;

    // Open project from dashboard
    await page.click('text=Open Project');

    // Should load PRD tab automatically
    await expect(page.locator('text=Canonical 27-Section PRD Specification')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=v1.0').first()).toBeVisible();

    // Verify canonical section titles render
    await expect(page.locator('text=2. Executive Summary')).toBeVisible();
    await expect(page.locator('text=4. Problem Statement')).toBeVisible();
    await expect(page.locator('text=12. Functional Requirements')).toBeVisible();

    // Edit a section (4. Problem Statement)
    const editBtn = page.locator('div:has-text("4. Problem Statement") button:has-text("Edit / Regenerate")').first();
    await editBtn.click();

    // Modal should open
    await expect(page.locator('text=Edit section content or regenerate with local AI')).toBeVisible();
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();

    // Modify content
    const updatedContent = 'CRITICAL EDITED PROBLEM STATEMENT: Verification of section update persistence.';
    await textarea.fill(updatedContent);

    // Save changes
    await page.click('button:has-text("Save Changes")');

    // Modal should close and section content should be updated
    await expect(page.locator(`text=${updatedContent}`)).toBeVisible();

    // Version should increment to v1.1
    await expect(page.locator('text=v1.1').first()).toBeVisible();

    // Verify historical versions remain immutable
    await page.click('text=7. Versions');
    await expect(page.locator('text=Document Version History')).toBeVisible();
    await expect(page.locator('text=v1.0').first()).toBeVisible();
    await expect(page.locator('text=v1.1').first()).toBeVisible();
  });

  test('G.4 - G.8: Export Markdown, DOCX, and PDF from UI', async ({ monitoredPage }) => {
    const { page } = monitoredPage;

    // Open project
    await page.click('text=Open Project');
    await expect(page.locator('text=Canonical 27-Section PRD Specification')).toBeVisible({ timeout: 10000 });

    // Switch to Export tab
    await page.click('button:has-text("8. Export")');
    await expect(page.locator('text=PRD Export Center')).toBeVisible();

    // Verify export buttons / cards are visible
    await expect(page.locator('text=Markdown (.md)')).toBeVisible();
    await expect(page.locator('text=Microsoft Word (.docx)')).toBeVisible();
    await expect(page.locator('text=Adobe PDF (.pdf)')).toBeVisible();

    // Test download Markdown
    const [downloadMd] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('a:has-text("Markdown (.md)")').click()
    ]);
    const mdPath = await downloadMd.path();
    expect(mdPath).toBeTruthy();

    // Verify file content is NOT an unauthorized error
    const fs = await import('fs');
    if (mdPath) {
      const content = fs.readFileSync(mdPath, 'utf-8');
      expect(content).not.toContain('Not authenticated');
      expect(content).toContain('Product Requirements Document');
    }

    // Test download DOCX
    const [downloadDocx] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('a:has-text("Microsoft Word (.docx)")').click()
    ]);
    const docxPath = await downloadDocx.path();
    expect(docxPath).toBeTruthy();
    if (docxPath) {
      const docxBuffer = fs.readFileSync(docxPath);
      expect(docxBuffer.subarray(0, 2).toString()).toBe('PK');
    }

    // Test download PDF
    const [downloadPdf] = await Promise.all([
      page.waitForEvent('download'),
      page.locator('a:has-text("Adobe PDF (.pdf)")').click()
    ]);
    const pdfPath = await downloadPdf.path();
    expect(pdfPath).toBeTruthy();
    if (pdfPath) {
      const pdfBuffer = fs.readFileSync(pdfPath);
      expect(pdfBuffer.subarray(0, 4).toString()).toBe('%PDF');
    }
  });
});

