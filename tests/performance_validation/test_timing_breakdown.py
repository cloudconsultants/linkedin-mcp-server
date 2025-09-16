#!/usr/bin/env python3
"""Test to isolate where the 40s is being spent in NO_STEALTH extraction."""

import asyncio
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"


async def test_timing_breakdown():
    """Break down timing to find the 40s bottleneck."""
    total_start = time.time()

    try:
        from patchright.async_api import async_playwright
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

        print("=== TIMING BREAKDOWN TEST ===")

        # Browser setup
        browser_start = time.time()
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()
        browser_time = time.time() - browser_start
        print(f"1. Browser init: {browser_time:.2f}s")

        # Cookie setup
        cookie_start = time.time()
        cookie = os.getenv("LINKEDIN_COOKIE")
        if cookie:
            await context.add_cookies(
                [
                    {
                        "name": "li_at",
                        "value": cookie,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }
                ]
            )
        cookie_time = time.time() - cookie_start
        print(f"2. Cookie setup: {cookie_time:.2f}s")

        # Create scraper
        scraper_start = time.time()
        scraper = ProfilePageScraper()
        profile_url = "https://www.linkedin.com/in/drihs/"
        scraper_time = time.time() - scraper_start
        print(f"3. Scraper creation: {scraper_time:.2f}s")

        # Time just the scrape_page call (centralized stealth + extraction)
        scrape_start = time.time()
        person = await scraper.scrape_page(
            page, profile_url, fields=PersonScrapingFields.ALL
        )
        scrape_time = time.time() - scrape_start
        print(f"4. scrape_page() call: {scrape_time:.2f}s ⚠️")

        # Cleanup
        cleanup_start = time.time()
        await browser.close()
        await playwright.stop()
        cleanup_time = time.time() - cleanup_start
        print(f"5. Cleanup: {cleanup_time:.2f}s")

        total_time = time.time() - total_start
        print(f"\nTOTAL: {total_time:.2f}s")

        print(f"\n📊 Results: {len(person.experiences)} experiences extracted")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_timing_breakdown())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")
