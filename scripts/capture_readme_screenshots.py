import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

USERNAME = "testuser_1793948736"
PASSWORD = "Password123!"
PROJECT_NAME = "AI Customer Support Suite"

async def capture_readme_screenshots():
    screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2
        )
        page = await context.new_page()

        print("Navigating to http://localhost:3000/...")
        await page.goto("http://localhost:3000/")
        await page.wait_for_timeout(1000)

        # Authenticate
        user_input = page.locator('input[type="text"]')
        if await user_input.count() > 0:
            print(f"Logging in as {USERNAME}...")
            await user_input.fill(USERNAME)
            await page.locator('input[type="password"]').fill(PASSWORD)
            await page.locator('button:has-text("Sign In Locally")').click()
            await page.wait_for_timeout(2000)

        # 1. Capture Dashboard (01-dashboard.png)
        print("Capturing 01-dashboard.png...")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(screenshots_dir / "01-dashboard.png"))

        # Select project
        print(f"Selecting project '{PROJECT_NAME}'...")
        proj_card = page.locator(f'h3:has-text("{PROJECT_NAME}")').first
        if await proj_card.count() > 0:
            await proj_card.click()
        else:
            first_proj = page.locator('h3').first
            await first_proj.click()
        await page.wait_for_timeout(1500)

        # Helper to click tab by selector
        async def click_tab(tab_name: str):
            btn = page.locator(f'button[data-tab="{tab_name}"]').first
            if await btn.count() > 0:
                await btn.click()
                await page.wait_for_timeout(800)

        # 2. Capture Submit Idea (02-submit-idea.png)
        print("Capturing 02-submit-idea.png...")
        await click_tab("input")
        await page.screenshot(path=str(screenshots_dir / "02-submit-idea.png"))

        # 3. Capture AI Analysis (03-ai-analysis.png)
        print("Capturing 03-ai-analysis.png...")
        await click_tab("analysis")
        await page.screenshot(path=str(screenshots_dir / "03-ai-analysis.png"))

        # 4. Capture Clarifications (04-clarifications.png)
        print("Capturing 04-clarifications.png...")
        await click_tab("clarifications")
        await page.screenshot(path=str(screenshots_dir / "04-clarifications.png"))

        # 5. Capture PRD Document (05-prd-document.png)
        print("Capturing 05-prd-document.png...")
        await click_tab("prd")
        # Ensure document is visible and scrolled to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(screenshots_dir / "05-prd-document.png"))

        # 6. Capture Requirements Matrix (06-requirements-matrix.png)
        print("Capturing 06-requirements-matrix.png...")
        await click_tab("requirements")
        await page.screenshot(path=str(screenshots_dir / "06-requirements-matrix.png"))

        # 7. Capture Quality Validation (07-quality-validation.png)
        print("Capturing 07-quality-validation.png...")
        await click_tab("validation")
        await page.screenshot(path=str(screenshots_dir / "07-quality-validation.png"))

        # 8. Capture Version History (08-version-history.png)
        print("Capturing 08-version-history.png...")
        await click_tab("history")
        await page.screenshot(path=str(screenshots_dir / "08-version-history.png"))

        # 9. Capture Document Export (09-document-export.png)
        print("Capturing 09-document-export.png...")
        # Switch to PRD document and open Document Details Drawer which highlights export options & metadata
        await click_tab("prd")
        details_btn = page.locator('button:has-text("Details")').first
        if await details_btn.count() > 0:
            await details_btn.click()
            await page.wait_for_timeout(800)
        await page.screenshot(path=str(screenshots_dir / "09-document-export.png"))

        await context.close()
        await browser.close()
    print("Successfully captured all 9 README screenshots!")

if __name__ == "__main__":
    asyncio.run(capture_readme_screenshots())
