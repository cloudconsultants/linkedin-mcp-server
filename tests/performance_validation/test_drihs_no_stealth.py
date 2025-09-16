#!/usr/bin/env python3
"""Test drihs profile extraction with NO_STEALTH for performance measurement."""

import asyncio
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set NO_STEALTH profile for maximum performance
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"


async def test_drihs_no_stealth():
    """Test drihs profile extraction with NO_STEALTH profile."""
    print("=" * 60)
    print("Starting drihs profile extraction with NO_STEALTH")
    print("=" * 60)
    print(f"🔧 Environment: STEALTH_PROFILE={os.environ.get('STEALTH_PROFILE')}")
    print(f"🔧 Use new stealth: USE_NEW_STEALTH={os.environ.get('USE_NEW_STEALTH')}")

    total_start = time.time()

    try:
        from patchright.async_api import async_playwright
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

        # Start browser
        browser_start = time.time()
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()
        browser_time = time.time() - browser_start
        print(f"✓ Browser initialized in {browser_time:.2f}s")

        # Add LinkedIn cookie
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
            print("✓ LinkedIn cookie added")

        # Create scraper with NO_STEALTH profile
        scraper = ProfilePageScraper()
        profile_url = "https://www.linkedin.com/in/drihs/"

        print("\n" + "=" * 60)
        print("CENTRALIZED STEALTH ARCHITECTURE (NO_STEALTH)")
        print("=" * 60)

        extraction_start = time.time()

        # Use proper centralized stealth architecture
        person = await scraper.scrape_page(
            page, profile_url, fields=PersonScrapingFields.ALL
        )

        extraction_time = time.time() - extraction_start
        total_time = time.time() - total_start

        # Save result
        result = person.model_dump(mode="json")
        output_file = f"drihs_no_stealth_{int(time.time())}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Print results
        print("\n" + "=" * 60)
        print("EXTRACTION RESULTS")
        print("=" * 60)
        print("✅ Extraction completed successfully!")
        print(f"📁 Results saved to: {output_file}")

        print("\n📊 Data Statistics:")
        print(f"   • Name: {person.name}")
        print(
            f"   • Headline: {person.headline[:50]}..."
            if person.headline
            else "   • Headline: None"
        )
        print(f"   • Location: {person.location}")
        print(f"   • About: {len(person.about[0]) if person.about else 0} characters")
        print(f"   • Experiences: {len(person.experiences)}")
        print(f"   • Education: {len(person.educations)}")
        print(f"   • Languages: {len(person.languages)}")
        print(f"   • Interests: {len(person.interests)}")
        print(f"   • Connection count: {person.connection_count}")
        print(f"   • Followers count: {person.followers_count}")
        print(f"   • Website URL: {person.website_url}")

        # Print timing summary
        print("\n⏱️  Performance Summary:")
        print(f"   • Browser init: {browser_time:.2f}s")
        print(f"   • Stealth + Extraction: {extraction_time:.2f}s")
        print(f"   • Total time: {total_time:.2f}s")

        # Performance verdict
        if extraction_time < 5:
            print(
                f"\n🚀 EXCELLENT: Centralized stealth architecture working perfectly in {extraction_time:.2f}s"
            )
        elif extraction_time < 10:
            print(
                f"\n✅ GOOD: Stealth + extraction completed in {extraction_time:.2f}s (< 10s target)"
            )
        elif extraction_time < 20:
            print(f"\n⚠️  ACCEPTABLE: Stealth + extraction took {extraction_time:.2f}s")
        else:
            print(f"\n⚠️  SLOW: Stealth + extraction took {extraction_time:.2f}s")

        # Cleanup
        await browser.close()
        await playwright.stop()

        return {
            "success": True,
            "extraction_time": extraction_time,
            "total_time": total_time,
            "output_file": output_file,
            "experiences": len(person.experiences),
            "education": len(person.educations),
        }

    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = asyncio.run(test_drihs_no_stealth())

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    if result["success"]:
        print(f"✅ SUCCESS - Extraction time: {result['extraction_time']:.2f}s")
        print(f"📁 Output file: {result['output_file']}")
    else:
        print(f"❌ FAILED - Error: {result['error']}")
