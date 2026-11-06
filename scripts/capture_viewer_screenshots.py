import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

USERNAME = "testuser_1793948736"
PASSWORD = "Password123!"
PROJECT_NAME = "AI Customer Support Suite"

async def capture_all_screenshots():
    screenshots_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    viewports = [
        {"name": "desktop", "width": 1280, "height": 800, "filename": "document_viewer_desktop.png"},
        {"name": "tablet", "width": 768, "height": 1024, "filename": "document_viewer_tablet.png"},
        {"name": "mobile", "width": 375, "height": 812, "filename": "document_viewer_mobile.png"},
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for vp in viewports:
            print(f"\nCapturing {vp['name']} ({vp['width']}x{vp['height']})...")
            context = await browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=2
            )
            page = await context.new_page()

            # 1. Navigate to root
            await page.goto("http://localhost:3000/")
            await page.wait_for_timeout(1000)

            # 2. Authenticate
            user_input = page.locator('input[type="text"]')
            if await user_input.count() > 0:
                print("  Logging in via UI...")
                await user_input.fill(USERNAME)
                await page.locator('input[type="password"]').fill(PASSWORD)
                await page.locator('button:has-text("Sign In Locally")').click()
                await page.wait_for_timeout(2000)

            # 3. Select project
            print(f"  Selecting project '{PROJECT_NAME}'...")
            proj_card = page.locator(f'h3:has-text("{PROJECT_NAME}")')
            await proj_card.wait_for(state="visible", timeout=10000)
            await proj_card.click()
            await page.wait_for_timeout(1500)

            # 4. Click PRD Document tab if needed
            tab_btn = page.locator('button:has-text("PRD Document")')
            if await tab_btn.count() > 0:
                await tab_btn.click()
                print("  Clicked 'PRD Document' tab")

            # 5. Wait for document container
            doc_container = page.locator('.document-container').first
            await doc_container.wait_for(state="visible", timeout=10000)
            print("  Document container is visible")

            # Allow fonts and layout to settle
            await page.wait_for_timeout(2000)

            # 6. Viewport specific interactions
            if vp["name"] == "desktop":
                toc_item = page.locator('button:has-text("Functional Requirements")').first
                if await toc_item.is_visible():
                    print("  Testing desktop TOC click...")
                    await toc_item.click()
                    await page.wait_for_timeout(800)
            elif vp["name"] == "tablet":
                print("  Tablet view: verifying continuous document reading layout...")
                # Scroll to display tables & criteria
                await page.evaluate("window.scrollTo(0, 300)")
                await page.wait_for_timeout(500)
            elif vp["name"] == "mobile":
                print("  Mobile view: checking responsive toolbar and document layout...")
                await page.evaluate("window.scrollTo(0, 200)")
                await page.wait_for_timeout(500)

            out_path = screenshots_dir / vp["filename"]
            await page.screenshot(path=str(out_path), full_page=False)
            print(f"  Saved screenshot: {out_path} ({out_path.stat().st_size} bytes)")

            await context.close()

        await browser.close()
    print("\nAll viewport screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all_screenshots())
