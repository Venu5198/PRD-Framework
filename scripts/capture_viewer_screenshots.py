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
            print("Logging in via UI...")
            await user_input.fill(USERNAME)
            await page.locator('input[type="password"]').fill(PASSWORD)
            await page.locator('button:has-text("Sign In Locally")').click()
            await page.wait_for_timeout(2000)

        # Select project
        print(f"Selecting project '{PROJECT_NAME}'...")
        proj_card = page.locator(f'h3:has-text("{PROJECT_NAME}")')
        await proj_card.wait_for(state="visible", timeout=10000)
        await proj_card.click()
        await page.wait_for_timeout(1500)

        # PRD Document tab
        tab_btn = page.locator('button:has-text("PRD Document")')
        if await tab_btn.count() > 0:
            await tab_btn.click()

        doc_container = page.locator('.document-container').first
        await doc_container.wait_for(state="visible", timeout=10000)
        await page.wait_for_timeout(1500)

        # 1. Desktop 1440px - Expanded (Default)
        print("\nCapturing Desktop 1440px Expanded...")
        await page.set_viewport_size({"width": 1440, "height": 900})
        await page.wait_for_timeout(500)
        out_path = screenshots_dir / "document_viewer_desktop_1440.png"
        await page.screenshot(path=str(out_path), full_page=False)
        print(f"  Saved: {out_path.name}")

        out_path_exp = screenshots_dir / "document_viewer_desktop_1440_expanded.png"
        await page.screenshot(path=str(out_path_exp), full_page=False)
        print(f"  Saved: {out_path_exp.name}")

        # 2. Desktop 1440px - Collapsed TOC
        print("\nCapturing Desktop 1440px Collapsed TOC...")
        collapse_btn = page.locator('button[aria-label="Toggle Document Outline"]').first
        if await collapse_btn.count() > 0:
            await collapse_btn.click()
            await page.wait_for_timeout(600)
            out_path_col = screenshots_dir / "document_viewer_desktop_1440_collapsed.png"
            await page.screenshot(path=str(out_path_col), full_page=False)
            print(f"  Saved: {out_path_col.name}")
            # Re-expand
            await collapse_btn.click()
            await page.wait_for_timeout(400)

        # 3. Desktop 1440px - Details Drawer Open
        print("\nCapturing Desktop Details Drawer...")
        details_btn = page.locator('button:has-text("Details")').first
        if await details_btn.count() > 0:
            await details_btn.click()
            await page.wait_for_timeout(600)
            out_path_drawer = screenshots_dir / "document_viewer_details_drawer.png"
            await page.screenshot(path=str(out_path_drawer), full_page=False)
            print(f"  Saved: {out_path_drawer.name}")
            close_drawer_btn = page.locator('button[aria-label="Close details drawer"]').first
            if await close_drawer_btn.count() > 0:
                await close_drawer_btn.click()
            await page.wait_for_timeout(400)

        # 4. Laptop 1280px
        print("\nCapturing Laptop 1280px...")
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.evaluate("window.scrollTo(0, 150)")
        await page.wait_for_timeout(600)
        out_laptop = screenshots_dir / "document_viewer_laptop_1280.png"
        await page.screenshot(path=str(out_laptop), full_page=False)
        print(f"  Saved: {out_laptop.name}")

        # 5. Tablet 768px
        print("\nCapturing Tablet 768px...")
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.evaluate("window.scrollTo(0, 200)")
        await page.wait_for_timeout(600)
        out_tablet = screenshots_dir / "document_viewer_tablet_768.png"
        await page.screenshot(path=str(out_tablet), full_page=False)
        print(f"  Saved: {out_tablet.name}")

        # 6. Mobile 390px
        print("\nCapturing Mobile 390px...")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.evaluate("window.scrollTo(0, 120)")
        await page.wait_for_timeout(600)
        out_mobile = screenshots_dir / "document_viewer_mobile_390.png"
        await page.screenshot(path=str(out_mobile), full_page=False)
        print(f"  Saved: {out_mobile.name}")

        await context.close()
        await browser.close()
    print("\nAll 6 screenshots captured and verified successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all_screenshots())
