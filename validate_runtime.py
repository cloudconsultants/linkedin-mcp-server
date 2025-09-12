#!/usr/bin/env python3
"""Validate runtime Docker image functionality."""

import asyncio
import os
import sys
from linkedin_mcp_server.server import create_mcp_server


async def validate_runtime():
    """Test all critical components."""
    tests = []

    # Test 1: Import all required modules
    try:
        import fastmcp  # noqa: F401
        import keyring  # noqa: F401
        import pydantic  # noqa: F401
        import patchright  # noqa: F401

        # Note: patchright provides playwright.async_api
        from patchright.async_api import async_playwright  # noqa: F401
        import fake_useragent  # noqa: F401
        import asyncio_throttle  # noqa: F401
        import rapidfuzz  # noqa: F401

        tests.append(("Module imports", True))
        print("✅ All required modules imported successfully")
    except ImportError as e:
        tests.append(("Module imports", f"Failed: {e}"))
        print(f"❌ Module import failed: {e}")

    # Test 2: Check Patchright browser availability
    browser_available = False
    try:
        from patchright.async_api import async_playwright

        async with async_playwright() as p:
            # Try to launch browser briefly to check installation
            browser = await p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            await browser.close()
            browser_available = True
            print("✅ Patchright browser launches successfully")
    except Exception as e:
        print(f"❌ Patchright browser failed: {e}")

    tests.append(("Browser availability", browser_available))

    # Test 3: Server initialization
    try:
        _ = create_mcp_server()  # Create server but don't store it
        tests.append(("Server creation", True))
        print("✅ Server created successfully")
    except Exception as e:
        tests.append(("Server creation", f"Failed: {e}"))
        print(f"❌ Server creation failed: {e}")

    # Test 4: Check tools registration (only implemented tools)
    try:
        from linkedin_mcp_server.tools import person

        # Only check person tools since company/job are not implemented yet
        tools_ok = hasattr(person, "get_person_profile")
        tests.append(("Person tools registration", tools_ok))
        if tools_ok:
            print("✅ Person LinkedIn tools registered successfully")
            print("⚠️  Company and job tools not yet implemented (expected)")
        else:
            print("❌ Person LinkedIn tools missing")
    except Exception as e:
        tests.append(("Person tools registration", f"Failed: {e}"))
        print(f"❌ Person tools registration failed: {e}")

    # Test 5: Check Docker runtime environment
    docker_runtime = os.environ.get("DOCKER_RUNTIME") == "1"
    tests.append(("Docker runtime env", docker_runtime))
    if docker_runtime:
        print("✅ Docker runtime environment configured")
    else:
        print("⚠️  Not running in Docker runtime mode")

    # Print results summary
    print("\n=== Runtime Validation Results ===")
    passed = 0
    total = len(tests)

    for test_name, result in tests:
        if result is True:
            status = "✅ PASS"
            passed += 1
        else:
            status = f"❌ FAIL: {result}"
        print(f"{test_name}: {status}")

    print(f"\nSummary: {passed}/{total} tests passed")

    # Return success if all critical tests passed (allow Docker env warning)
    critical_passed = all(
        r is True
        for name, r in tests
        if name != "Docker runtime env"  # This is informational only
    )

    return critical_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(validate_runtime())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation failed with exception: {e}")
        sys.exit(1)
