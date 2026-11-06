import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

USERNAME = "testuser_1793948736"
PASSWORD = "Password123!"
PROJECT_NAME = "AI Customer Support Suite"

VIEWPORTS = [
    {"name": "mobile_390", "width": 390, "height": 844, "label": "Mobile (390px)"},
    {"name": "mobile_430", "width": 430, "height": 932, "label": "Mobile Large (430px)"},
    {"name": "tablet_768", "width": 768, "height": 1024, "label": "Tablet Portrait (768px)"},
    {"name": "tablet_1024", "width": 1024, "height": 768, "label": "Tablet Landscape (1024px)"},
    {"name": "laptop_1280", "width": 1280, "height": 800, "label": "Laptop (1280px)"},
    {"name": "desktop_1440", "width": 1440, "height": 900, "label": "Desktop Standard (1440px)"},
    {"name": "desktop_1920", "width": 1920, "height": 1080, "label": "Desktop Wide (1920px)"},
]

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

        # Authenticate if needed
        user_input = page.locator('input[type="text"]')
        if await user_input.count() > 0:
            print("Logging in via UI...")
            await user_input.fill(USERNAME)
            await page.locator('input[type="password"]').fill(PASSWORD)
            await page.locator('button:has-text("Sign In Locally")').click()
            await page.wait_for_timeout(2000)

        # Select project
        print(f"Selecting project '{PROJECT_NAME}'...")
        proj_card = page.locator(f'h3:has-text("{PROJECT_NAME}")').first
        if await proj_card.count() > 0:
            await proj_card.click()
            await page.wait_for_timeout(1500)
        else:
            # Click first available project card
            first_proj = page.locator('h3').first
            await first_proj.click()
            await page.wait_for_timeout(1500)

        # Ensure PRD Document tab is open
        tab_btn = page.locator('button:has-text("PRD Document")').first
        if await tab_btn.count() > 0:
            await tab_btn.click()

        doc_container = page.locator('.document-container').first
        await doc_container.wait_for(state="visible", timeout=10000)
        await page.wait_for_timeout(1000)

        # Capture each of the 7 viewports
        for vp in VIEWPORTS:
            print(f"Capturing {vp['label']} ({vp['width']}x{vp['height']})...")
            await page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(600)
            out_file = screenshots_dir / f"responsive_{vp['name']}.png"
            await page.screenshot(path=str(out_file), full_page=False)
            print(f"  Saved: {out_file.name}")

        # Capture Desktop Details Drawer
        print("Capturing Desktop Details Drawer...")
        await page.set_viewport_size({"width": 1440, "height": 900})
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

        # Capture Mobile 390px Details Drawer
        print("Capturing Mobile 390px Details Drawer...")
        await page.set_viewport_size({"width": 390, "height": 844})
        more_btn = page.locator('button[aria-label="More document actions"]').first
        if await more_btn.count() > 0:
            await more_btn.click()
            await page.wait_for_timeout(300)
            mobile_details_btn = page.locator('button:has-text("Document Details")').first
            if await mobile_details_btn.count() > 0:
                await mobile_details_btn.click()
                await page.wait_for_timeout(600)
                out_path_mob_drawer = screenshots_dir / "responsive_mobile_390_drawer.png"
                await page.screenshot(path=str(out_path_mob_drawer), full_page=False)
                print(f"  Saved: {out_path_mob_drawer.name}")

        await context.close()
        await browser.close()
    print("\nAll responsive screenshots captured successfully across all 7 viewports!")

if __name__ == "__main__":
    asyncio.run(capture_all_screenshots())
