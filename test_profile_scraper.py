#!/usr/bin/env python3
"""
Test script to validate current LinkedIn profile scraper against testscrape.txt baseline.
Tests the profile: amir-nahvi-94814819
"""

import asyncio
import json
from datetime import datetime
from linkedin_mcp_server.tools.person import get_person_profile


async def test_profile_scraper():
    """Test the current profile scraper against testscrape.txt profile."""

    # Profile from testscrape.txt
    test_username = "amir-nahvi-94814819"

    print("🧪 Testing LinkedIn MCP Server Profile Scraper")
    print(f"📝 Profile: {test_username}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    try:
        print("⏳ Starting comprehensive profile scraping...")

        # Time the operation to detect any timeouts/kick-outs
        start_time = asyncio.get_event_loop().time()

        result = await get_person_profile(test_username)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        print(f"✅ Scraping completed in {duration:.2f} seconds")
        print("-" * 60)
        print("📊 RESULTS:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 60)

        # Basic validation
        if isinstance(result, dict):
            if "error" in result:
                print(f"❌ ERROR DETECTED: {result}")
                return False

            # Check for key fields from testscrape.txt
            expected_fields = [
                "name",
                "about",
                "experiences",
                "educations",
                "interests",
                "accomplishments",
                "contacts",
                "company",
                "job_title",
                "open_to_work",
            ]

            missing_fields = [field for field in expected_fields if field not in result]
            if missing_fields:
                print(f"⚠️  Missing fields: {missing_fields}")
            else:
                print("✅ All expected fields present")

            # Check if we got actual data
            if result.get("name"):
                print(f"✅ Name extracted: {result['name']}")
            else:
                print("❌ Name not extracted")

            if result.get("experiences"):
                print(f"✅ Experiences extracted: {len(result['experiences'])} items")
            else:
                print("❌ No experiences extracted")

            if result.get("educations"):
                print(f"✅ Education extracted: {len(result['educations'])} items")
            else:
                print("❌ No education extracted")

            return True
        else:
            print(f"❌ Unexpected result type: {type(result)}")
            return False

    except Exception as e:
        print(f"❌ EXCEPTION OCCURRED: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback

        print("Full traceback:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_profile_scraper())

    if success:
        print("🎉 Test completed successfully")
    else:
        print("💥 Test failed")
        exit(1)
