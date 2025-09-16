#!/usr/bin/env python3
"""
Test improved extraction with all fixes applied.

Validates:
1. ✅ Experience field mapping (position vs company separation)
2. ✅ Date parsing handling 'Present' correctly
3. ✅ Missing website URL extraction (cloudconsultants.ch)
4. ✅ Missing followers count extraction
5. ✅ Location extraction from experience entries
6. ✅ Duration field extraction (already present on page)
"""

import asyncio
import json
import os
import time

# Set NO_STEALTH environment
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"

from linkedin_mcp_server import get_person_profile


async def test_improved_extraction():
    """Test the improved extraction with all fixes."""
    print("🚀 TESTING IMPROVED EXTRACTION")
    print("=" * 50)
    print(f"Environment: STEALTH_PROFILE={os.environ.get('STEALTH_PROFILE')}")
    print("Target: drihs LinkedIn profile")
    print()

    start_time = time.time()

    try:
        # Run extraction (authentication handled automatically)
        print("🔍 Starting extraction...")
        result = await get_person_profile("drihs")

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"⏱️  TOTAL EXECUTION TIME: {execution_time:.2f}s")
        print()

        # Validate results
        person = result.get("person") if isinstance(result, dict) else result

        if not person:
            print("❌ No person data extracted")
            return

        # Save results
        timestamp = int(time.time())
        filename = f"drihs_improved_extraction_{timestamp}.json"

        # Convert to JSON-serializable format
        if hasattr(person, "model_dump"):
            person_data = person.model_dump()
        else:
            person_data = person

        with open(filename, "w") as f:
            json.dump(person_data, f, indent=2, default=str)

        print(f"💾 Results saved to: {filename}")
        print()

        # Validation checks
        print("🔍 VALIDATION RESULTS:")
        print("-" * 30)

        # Experience validation
        experiences = person_data.get("experiences", [])
        print(f"📋 Experiences: {len(experiences)}")

        if experiences:
            first_exp = experiences[0]
            print("   First Experience:")
            print(f"   • Position: '{first_exp.get('position_title', 'N/A')}'")
            print(f"   • Company: '{first_exp.get('institution_name', 'N/A')}'")
            print(f"   • From: '{first_exp.get('from_date', 'N/A')}'")
            print(f"   • To: '{first_exp.get('to_date', 'N/A')}'")
            print(f"   • Duration: '{first_exp.get('duration', 'N/A')}'")
            print(f"   • Location: '{first_exp.get('location', 'N/A')}'")
            print(f"   • Employment: '{first_exp.get('employment_type', 'N/A')}'")

            # Validation checks
            checks = {
                "Position correct": first_exp.get("position_title")
                == "Managing Director",
                "Company correct": first_exp.get("institution_name")
                == "Cloud Consultants GmbH",
                "From date correct": first_exp.get("from_date") == "Sep 2022",
                "Present date handled": first_exp.get("to_date") is None,
                "Duration extracted": first_exp.get("duration") == "3 yrs 1 mo",
                "Location correct": first_exp.get("location") == "Greater Zurich Area",
                "Employment type": first_exp.get("employment_type") == "Full-time",
            }

            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check}")

        # Education validation
        educations = person_data.get("educations", [])
        print(f"\n🎓 Education: {len(educations)}")

        # Metadata validation
        print("\n📊 Metadata:")
        followers = person_data.get("followers_count")
        website = person_data.get("website_url")
        connection_count = person_data.get("connection_count")

        print(f"   • Followers: {followers}")
        print(f"   • Website: {website}")
        print(f"   • Connections: {connection_count}")

        metadata_checks = {
            "Followers extracted": followers is not None,
            "Website extracted": website is not None
            and "cloudconsultants" in str(website).lower(),
            "Connections extracted": connection_count is not None,
        }

        for check, passed in metadata_checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")

        # Overall summary
        print("\n🎯 SUMMARY:")
        print(f"   ✅ Extraction completed in {execution_time:.2f}s")
        print(f"   ✅ {len(experiences)} experiences extracted")
        print(f"   ✅ {len(educations)} education entries")

        # Check if all critical fixes work
        critical_fixes = [
            experiences and len(experiences) >= 5,
            experiences
            and experiences[0].get("institution_name") == "Cloud Consultants GmbH",
            experiences and experiences[0].get("from_date") == "Sep 2022",
            experiences and experiences[0].get("to_date") is None,
            experiences and experiences[0].get("duration") == "3 yrs 1 mo",
            experiences and experiences[0].get("location") == "Greater Zurich Area",
        ]

        fixes_working = sum(critical_fixes)
        print(f"   📈 Critical fixes working: {fixes_working}/6")

        if fixes_working >= 5:
            print("   🎉 EXTRACTION SIGNIFICANTLY IMPROVED!")
        else:
            print("   ⚠️  Some issues remain")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_improved_extraction())
