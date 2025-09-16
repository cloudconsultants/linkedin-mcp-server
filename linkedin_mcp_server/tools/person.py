# linkedin_mcp_server/tools/person.py
"""
LinkedIn person profile scraping tools with Playwright-based dual scraping modes.

Provides MCP tools for extracting LinkedIn profile information with two modes:
- get_person_profile_minimal: Fast basic info scraping (~2-5 seconds)
- get_person_profile: Comprehensive profile scraping (~30 seconds)

Maintains exact compatibility with existing output format while using modern
Playwright automation for improved performance and reliability.
"""

import logging
import time
from typing import Any, Dict

from fastmcp import FastMCP

from linkedin_mcp_server.error_handler import handle_tool_error

logger = logging.getLogger(__name__)


async def get_person_profile_minimal(linkedin_username: str) -> Dict[str, Any]:
    """
    Get a person's LinkedIn profile with basic information only (fast mode).

    This tool scrapes only essential profile data for quick lookups.
    Performance target: <5 seconds with new stealth system, <2 seconds with NO_STEALTH profile.

    Args:
        linkedin_username (str): LinkedIn username (e.g., "stickerdaniel", "anistji")

    Returns:
        Dict[str, Any]: Basic profile data including name, headline, location, about, and current company
    """
    start_time = time.time()

    try:
        import os
        from patchright.async_api import async_playwright
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

        # Construct LinkedIn URL
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_username}/"

        # Set environment for optimal performance
        os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
        os.environ["USE_NEW_STEALTH"] = "true"

        # Start browser directly (like working test script)
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()

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
        else:
            raise ValueError("LINKEDIN_COOKIE environment variable not set")

        # Create scraper and use centralized scrape_page method
        scraper = ProfilePageScraper()
        person = await scraper.scrape_page(
            page, linkedin_url, fields=PersonScrapingFields.MINIMAL
        )

        # Clean up with error handling to prevent asyncio conflicts
        try:
            await browser.close()
        except Exception as e:
            logger.debug(f"Browser close error (non-critical): {e}")

        try:
            await playwright.stop()
        except Exception as e:
            logger.debug(f"Playwright stop error (non-critical): {e}")

        # Small delay to allow background cleanup to complete
        import asyncio

        await asyncio.sleep(0.1)

        # Calculate timing
        duration = time.time() - start_time

        # Return raw model output with performance metrics
        result = person.model_dump()
        result["_performance"] = {
            "duration_seconds": round(duration, 1),
            "stealth_system": "NEW (centralized)",
            "stealth_profile": "NO_STEALTH",
            "scraping_mode": "minimal",
        }
        return result

    except Exception as e:
        return handle_tool_error(e, "get_person_profile_minimal")


async def get_person_profile(linkedin_username: str) -> Dict[str, Any]:
    """
    Get a comprehensive person's LinkedIn profile with all available data.

    This tool scrapes complete profile information including experience, education,
    interests, accomplishments, and contacts. Maintains exact compatibility with
    existing output format.

    Performance targets:
    - Legacy system: ~300 seconds (5 minutes)
    - New stealth system: ~75 seconds with MINIMAL_STEALTH, ~50 seconds with NO_STEALTH

    Args:
        linkedin_username (str): LinkedIn username (e.g., "stickerdaniel", "anistji")

    Returns:
        Dict[str, Any]: Complete structured profile data matching testdata/testscrape.txt format
    """
    start_time = time.time()

    try:
        import os
        from patchright.async_api import async_playwright
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

        # Construct LinkedIn URL
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_username}/"

        # Set environment for optimal performance (match .env settings)
        os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
        os.environ["USE_NEW_STEALTH"] = "true"

        # Start browser directly (like working test script)
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()

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
        else:
            raise ValueError("LINKEDIN_COOKIE environment variable not set")

        # Create scraper and use centralized scrape_page method
        scraper = ProfilePageScraper()
        person = await scraper.scrape_page(
            page, linkedin_url, fields=PersonScrapingFields.ALL
        )

        # Clean up with error handling to prevent asyncio conflicts
        try:
            await browser.close()
        except Exception as e:
            logger.debug(f"Browser close error (non-critical): {e}")

        try:
            await playwright.stop()
        except Exception as e:
            logger.debug(f"Playwright stop error (non-critical): {e}")

        # Small delay to allow background cleanup to complete
        import asyncio

        await asyncio.sleep(0.1)

        # Calculate timing
        duration = time.time() - start_time

        # Return raw model output with performance metrics
        result = person.model_dump()
        result["_performance"] = {
            "duration_seconds": round(duration, 1),
            "stealth_system": "NEW (centralized)",
            "stealth_profile": "NO_STEALTH",
            "scraping_mode": "comprehensive",
        }
        return result

    except Exception as e:
        return handle_tool_error(e, "get_person_profile")


def register_person_tools(mcp: FastMCP) -> None:
    """
    Register all person-related tools with the MCP server.

    Args:
        mcp (FastMCP): The MCP server instance
    """
    # Register the standalone functions as MCP tools
    mcp.tool()(get_person_profile_minimal)
    mcp.tool()(get_person_profile)
