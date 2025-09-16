#!/usr/bin/env python3
"""
Test extraction fixes with proper cookie authentication.
Based on the working test_drihs_no_stealth.py pattern.
"""

import asyncio
import json
import os
import time

# Load environment from .env file
from dotenv import load_dotenv

load_dotenv()

# Set NO_STEALTH environment
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["LOG_LEVEL"] = "INFO"

from linkedin_mcp_server.authentication import get_authentication


async def test_fixes_with_authentication():
    """Test improved extraction with proper authentication."""
    print("🚀 TESTING EXTRACTION FIXES WITH AUTHENTICATION")
    print("=" * 60)

    start_time = time.time()

    try:
        # Get cookie for authentication
        print("🔐 Getting LinkedIn authentication...")
        cookie = get_authentication()
        if not cookie:
            print("❌ No LinkedIn authentication found")
            return

        print("✅ Authentication retrieved successfully")

        # Initialize browser (following test_drihs_no_stealth.py pattern)
        print("🌐 Initializing browser...")
        browser_start = time.time()

        from patchright.async_api import async_playwright
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()

        # Add LinkedIn cookie
        await context.add_cookies(
            [{"name": "li_at", "value": cookie, "domain": ".linkedin.com", "path": "/"}]
        )

        browser_time = time.time() - browser_start
        print(f"✅ Browser initialized in {browser_time:.2f}s")

        # Navigate to profile
        print("🔍 Navigating to drihs profile...")
        nav_start = time.time()
        await page.goto("https://www.linkedin.com/in/drihs/")
        await page.wait_for_timeout(3000)
        nav_time = time.time() - nav_start

        print(f"✅ Navigation completed in {nav_time:.2f}s")

        # Extract profile data using our improved scraper
        print("📋 Extracting profile data with fixes...")
        extract_start = time.time()

        scraper = ProfilePageScraper()
        person = await scraper.extract_data(page, PersonScrapingFields.ALL)

        extract_time = time.time() - extract_start
        total_time = time.time() - start_time

        print(f"✅ Extraction completed in {extract_time:.2f}s")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print()

        # Save results
        person_data = person.model_dump()
        timestamp = int(time.time())
        filename = f"drihs_fixes_validated_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(person_data, f, indent=2, default=str)

        print(f"💾 Results saved to: {filename}")
        print()

        # Validation
        print("🔍 VALIDATION RESULTS:")
        print("-" * 40)

        experiences = person_data.get("experiences", [])
        educations = person_data.get("educations", [])

        print(f"📋 Experiences extracted: {len(experiences)}")
        print(f"🎓 Education entries: {len(educations)}")

        if experiences:
            first_exp = experiences[0]
            print("\n   📌 First Experience Details:")
            print(f"      Position: '{first_exp.get('position_title', 'N/A')}'")
            print(f"      Company: '{first_exp.get('institution_name', 'N/A')}'")
            print(f"      From: '{first_exp.get('from_date', 'N/A')}'")
            print(f"      To: {first_exp.get('to_date', 'N/A')}")
            print(f"      Duration: '{first_exp.get('duration', 'N/A')}'")
            print(f"      Location: '{first_exp.get('location', 'N/A')}'")
            print(f"      Type: '{first_exp.get('employment_type', 'N/A')}'")

            # Critical validation checks
            expected_results = {
                "Position = 'Managing Director'": first_exp.get("position_title")
                == "Managing Director",
                "Company = 'Cloud Consultants GmbH'": first_exp.get("institution_name")
                == "Cloud Consultants GmbH",
                "From date = 'Sep 2022'": first_exp.get("from_date") == "Sep 2022",
                "Present handled (to_date=None)": first_exp.get("to_date") is None,
                "Duration = '3 yrs 1 mo'": first_exp.get("duration") == "3 yrs 1 mo",
                "Location = 'Greater Zurich Area'": first_exp.get("location")
                == "Greater Zurich Area",
                "Employment = 'Full-time'": first_exp.get("employment_type")
                == "Full-time",
            }

            print("\n   🎯 Experience Field Validation:")
            for check, result in expected_results.items():
                status = "✅" if result else "❌"
                print(f"      {status} {check}")

        # Metadata validation
        followers = person_data.get("followers_count")
        website = person_data.get("website_url")
        connections = person_data.get("connection_count")

        print("\n   📊 Metadata Validation:")
        print(f"      Followers: {followers}")
        print(f"      Website: {website}")
        print(f"      Connections: {connections}")

        metadata_checks = {
            "Followers extracted": followers is not None,
            "Website contains cloudconsultants": website
            and "cloudconsultants" in str(website).lower(),
            "Connections extracted": connections is not None,
        }

        for check, result in metadata_checks.items():
            status = "✅" if result else "❌"
            print(f"      {status} {check}")

        # Performance summary
        print("\n⚡ PERFORMANCE SUMMARY:")
        print(f"   🚀 Browser init: {browser_time:.2f}s")
        print(f"   🌐 Navigation: {nav_time:.2f}s")
        print(f"   📋 Extraction: {extract_time:.2f}s")
        print(f"   ⏱️  Total: {total_time:.2f}s")

        # Overall assessment
        all_checks = {**expected_results, **metadata_checks}
        passed = sum(all_checks.values())
        total = len(all_checks)
        success_rate = (passed / total) * 100

        print("\n🎉 FINAL ASSESSMENT:")
        print(f"   📈 Success rate: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("   ✅ EXTRACTION FIXES WORKING SUCCESSFULLY!")
        elif success_rate >= 60:
            print("   ⚠️  Good progress, some issues remain")
        else:
            print("   ❌ Significant issues detected")

        # Close browser
        await browser.close()
        await playwright.stop()
        print("\n🔒 Browser closed")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixes_with_authentication())
