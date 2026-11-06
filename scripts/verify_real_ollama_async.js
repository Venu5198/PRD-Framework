const { chromium } = require('../frontend/node_modules/@playwright/test');
const fs = require('fs');
const path = require('path');
const http = require('http');

async function run() {
  console.log('=== STARTING ASYNC REAL OLLAMA VERIFICATION ===');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();

  const results = {
    testProjectTitle: `AI Customer Support Assistant ${Date.now()}`,
    startTime: new Date().toISOString(),
    stages: [],
    jobId: null,
    projectId: null,
    modelName: 'llama3.2',
    provider: 'OllamaAdapter',
    durationSeconds: 0,
    status: 'UNKNOWN'
  };

  try {
    // 1. Login
    console.log('[1/8] Logging in as local_engineer...');
    await page.goto('http://localhost:3000/');
    await page.waitForSelector('text=PRD Framework', { timeout: 10000 });
    await page.fill('input[type="text"]:near(:text("Username"))', 'local_engineer');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForSelector('text=Idea in. Professional PRD out.', { timeout: 15000 });
    console.log('  -> Logged in successfully.');

    // 2. Create Project
    console.log('[2/8] Creating test project:', results.testProjectTitle);
    await page.click('button:has-text("New PRD Project")');
    await page.waitForSelector('text=Create New PRD Project', { timeout: 5000 });
    await page.fill('input[placeholder*="NextGen"]', results.testProjectTitle);
    await page.fill('textarea[placeholder*="Optional context"]', 'AI Customer Support Assistant with approved knowledge-base articles and human escalation.');
    await page.click('button[type="submit"]:has-text("Create & Proceed")');
    await page.waitForSelector(`h1:has-text("${results.testProjectTitle}")`, { timeout: 10000 });
    console.log('  -> Project created successfully.');

    // Extract project ID from URL
    const url = page.url();
    // Assuming URL or internal state, let's grab project ID
    console.log('  -> Current URL:', url);

    // 3. Submit Product Concept
    console.log('[3/8] Submitting product concept...');
    const inputConcept = 'Build an AI-powered customer support assistant that answers customer questions using approved knowledge-base articles, maintains conversation history, identifies uncertain answers, and escalates unresolved issues to human support agents.';
    await page.fill('textarea[placeholder*="Describe what you want to build"]', inputConcept);
    await page.click('button:has-text("Submit & Analyze Idea")');

    // Wait for analysis to complete
    console.log('  -> Waiting for Concept Analysis & Clarifications...');
    await page.waitForSelector('text=AI Input Analysis & Extraction', { timeout: 300000 });
    console.log('  -> Concept Analysis completed.');

    // 4. Navigate to PRD Document tab
    console.log('[4/8] Navigating to PRD Document tab...');
    await page.click('button:has-text("4. PRD Document")');
    await page.waitForSelector('button:has-text("Generate PRD Now")', { timeout: 10000 });

    // Listen for the 202 Accepted response on job creation
    let acceptedJobResponse = null;
    page.on('response', async (res) => {
      if (res.url().includes('/prd/generate') && res.request().method() === 'POST') {
        try {
          acceptedJobResponse = {
            status: res.status(),
            body: await res.json()
          };
          console.log('  [HTTP EVENT] POST /prd/generate ->', res.status(), JSON.stringify(acceptedJobResponse.body));
        } catch (e) {}
      }
    });

    // 5. Trigger PRD Generation
    console.log('[5/8] Clicking Generate PRD Now (Asynchronous Job Submission)...');
    const genStart = Date.now();
    await page.click('button:has-text("Generate PRD Now")');

    // Wait for async progress card to appear
    await page.waitForSelector('text=AI PRD Synthesis in Progress', { timeout: 15000 });
    console.log('  -> Asynchronous progress card rendered on UI!');

    // Wait for job ID to be populated
    await page.waitForTimeout(3000);
    if (acceptedJobResponse) {
      results.jobId = acceptedJobResponse.body.job_id;
      results.projectId = acceptedJobResponse.body.project_id;
    }

    // 6. Test Browser Refresh Mid-Generation (Session Recovery)
    console.log('[6/8] Refreshing browser mid-generation to verify session resumption...');
    await page.waitForTimeout(5000);
    await page.reload();
    await page.waitForSelector('text=AI PRD Synthesis in Progress', { timeout: 15000 });
    console.log('  -> Session recovery VERIFIED: Progress card restored after reload!');

    // 7. Monitor Job Progress Until Completion
    console.log('[7/8] Polling job progress through completion (real Ollama CPU inference)...');
    let completed = false;
    let lastProgress = -1;
    let lastStage = '';

    while (!completed) {
      await page.waitForTimeout(5000);
      const elapsedSec = Math.floor((Date.now() - genStart) / 1000);

      // Check if PRD document rendered
      const isDocRendered = await page.locator('text=Canonical 27-Section PRD Specification').isVisible();
      if (isDocRendered) {
        completed = true;
        results.durationSeconds = elapsedSec;
        results.status = 'COMPLETED';
        console.log(`\n>>> GENERATION COMPLETE in ${elapsedSec}s! <<<`);
        break;
      }

      // Check if failed
      const isFailed = await page.locator('text=PRD Generation Failed').isVisible();
      if (isFailed) {
        results.status = 'FAILED';
        results.durationSeconds = elapsedSec;
        const errText = await page.locator('p:has-text("ERROR")').innerText().catch(() => 'Unknown error');
        console.error(`\n>>> GENERATION FAILED in ${elapsedSec}s: ${errText} <<<`);
        break;
      }

      // Read current stage from DOM
      const stageText = await page.locator('span:has-text("Stage ")').innerText().catch(() => '');
      if (stageText && stageText !== lastStage) {
        lastStage = stageText;
        console.log(`  [T+${elapsedSec}s] ${stageText}`);
        results.stages.push({ time: elapsedSec, stage: stageText });
      }
    }

    // 8. Capture PRD Content & Export
    if (results.status === 'COMPLETED') {
      console.log('[8/8] Verifying PRD Document sections and exports...');
      await page.waitForSelector('text=v1.0', { timeout: 10000 });
      console.log('  -> PRD v1.0 active.');

      // Navigate to Export tab
      await page.click('button:has-text("8. Export")');
      await page.waitForSelector('text=PRD Export Center', { timeout: 10000 });

      // Download Markdown
      const [mdDownload] = await Promise.all([
        page.waitForEvent('download'),
        page.click('a:has-text("Markdown (.md)")')
      ]);
      const mdPath = path.join(__dirname, '..', 'docs', 'benchmark', 'generated_customer_support_prd.md');
      await mdDownload.saveAs(mdPath);
      console.log('  -> Saved Markdown export to:', mdPath);

      // Download PDF
      const [pdfDownload] = await Promise.all([
        page.waitForEvent('download'),
        page.click('a:has-text("PDF Document (.pdf)")')
      ]);
      const pdfPath = path.join(__dirname, '..', 'docs', 'benchmark', 'generated_customer_support_prd.pdf');
      await pdfDownload.saveAs(pdfPath);
      console.log('  -> Saved PDF export to:', pdfPath);

      results.mdPath = mdPath;
      results.pdfPath = pdfPath;
    }

    results.endTime = new Date().toISOString();
    fs.writeFileSync(
      path.join(__dirname, '..', 'docs', 'benchmark', 'async_verification_result.json'),
      JSON.stringify(results, null, 2)
    );
    console.log('=== VERIFICATION SCRIPT FINISHED SUCCESSFULLY ===');
  } catch (err) {
    console.error('FATAL ERROR DURING VERIFICATION:', err);
    await page.screenshot({ path: path.join(__dirname, '..', 'docs', 'benchmark', 'error_screenshot.png') });
  } finally {
    await browser.close();
  }
}

run();
