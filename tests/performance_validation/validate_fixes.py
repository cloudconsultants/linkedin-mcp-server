#!/usr/bin/env python3
"""
Validate extraction fixes using the MCP server approach.
"""

import asyncio
import json
import os
import time

# Set NO_STEALTH environment
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["LOG_LEVEL"] = "DEBUG"

from patchright.async_api import async_playwright


async def test_extraction_with_fixes():
    """Test the improved extraction directly."""
    print("🚀 VALIDATING EXTRACTION FIXES")
    print("=" * 50)

    async with async_playwright() as p:
        # Use the same browser setup as the MCP server
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-bgsync",
                "--disable-extensions-http-throttling",
                "--disable-extensions-file-access-check",
                "--disable-extensions",
                "--disable-plugins",
            ],
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to LinkedIn profile
            start_time = time.time()

            print("🌐 Navigating to drihs profile...")
            await page.goto("https://www.linkedin.com/in/drihs/")
            await page.wait_for_timeout(5000)  # Wait for page load

            # Import and test our improved ProfilePageScraper
            from linkedin_mcp_server.scraper.pages.profile_page import (
                ProfilePageScraper,
            )
            from linkedin_mcp_server.scraper.models.person import Person
            from linkedin_mcp_server.scraper.enums import PersonScrapingFields

            scraper = ProfilePageScraper()
            person = Person()

            print("🔍 Running improved extraction...")

            # Extract data using our improved scraper
            person = await scraper.extract_data(page, PersonScrapingFields.ALL)

            end_time = time.time()
            execution_time = end_time - start_time

            print(f"⏱️  EXTRACTION TIME: {execution_time:.2f}s")
            print()

            # Convert to dict and save
            person_data = person.model_dump()
            timestamp = int(time.time())
            filename = f"drihs_validated_fixes_{timestamp}.json"

            with open(filename, "w") as f:
                json.dump(person_data, f, indent=2, default=str)

            print(f"💾 Results saved to: {filename}")
            print()

            # Validate fixes
            print("🔍 VALIDATION RESULTS:")
            print("-" * 30)

            experiences = person_data.get("experiences", [])
            print(f"📋 Experiences: {len(experiences)}")

            if experiences:
                first_exp = experiences[0]
                print("   First Experience Analysis:")
                print(f"   • Position: '{first_exp.get('position_title', 'N/A')}'")
                print(f"   • Company: '{first_exp.get('institution_name', 'N/A')}'")
                print(f"   • From: '{first_exp.get('from_date', 'N/A')}'")
                print(f"   • To: '{first_exp.get('to_date', 'N/A')}'")
                print(f"   • Duration: '{first_exp.get('duration', 'N/A')}'")
                print(f"   • Location: '{first_exp.get('location', 'N/A')}'")
                print(f"   • Employment: '{first_exp.get('employment_type', 'N/A')}'")
                print()

                # Validation checks against screenshot
                checks = {
                    "✅ Position title = 'Managing Director'": first_exp.get(
                        "position_title"
                    )
                    == "Managing Director",
                    "✅ Company = 'Cloud Consultants GmbH'": first_exp.get(
                        "institution_name"
                    )
                    == "Cloud Consultants GmbH",
                    "✅ From date = 'Sep 2022'": first_exp.get("from_date")
                    == "Sep 2022",
                    "✅ Present date handled (to_date=None)": first_exp.get("to_date")
                    is None,
                    "✅ Duration = '3 yrs 1 mo'": first_exp.get("duration")
                    == "3 yrs 1 mo",
                    "✅ Location = 'Greater Zurich Area'": first_exp.get("location")
                    == "Greater Zurich Area",
                    "✅ Employment type = 'Full-time'": first_exp.get("employment_type")
                    == "Full-time",
                }

                for check_name, passed in checks.items():
                    status = "✅" if passed else "❌"
                    print(f"   {status} {check_name.split(' ', 1)[1]}")

            # Metadata validation
            print("\n📊 Metadata:")
            followers = person_data.get("followers_count")
            website = person_data.get("website_url")
            connection_count = person_data.get("connection_count")

            print(f"   • Followers: {followers}")
            print(f"   • Website: {website}")
            print(f"   • Connections: {connection_count}")

            metadata_checks = {
                "Followers count extracted": followers is not None,
                "Website URL contains cloudconsultants": website
                and "cloudconsultants" in str(website).lower(),
                "Connection count extracted": connection_count is not None,
            }

            for check, passed in metadata_checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check}")

            # Overall assessment
            print("\n🎯 OVERALL ASSESSMENT:")
            total_checks = len(checks) + len(metadata_checks)
            passed_checks = sum(checks.values()) + sum(metadata_checks.values())
            print(f"   📈 Checks passed: {passed_checks}/{total_checks}")

            if passed_checks >= total_checks * 0.8:
                print("   🎉 EXTRACTION FIXES SUCCESSFUL!")
            else:
                print("   ⚠️  More work needed")

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(test_extraction_with_fixes())
