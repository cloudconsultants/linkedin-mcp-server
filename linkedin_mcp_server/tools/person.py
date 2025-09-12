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
from typing import Any, Dict, List

from fastmcp import FastMCP

from linkedin_mcp_server.error_handler import handle_tool_error

logger = logging.getLogger(__name__)


async def get_person_profile_minimal(linkedin_username: str) -> Dict[str, Any]:
    """
    Get a person's LinkedIn profile with basic information only (fast mode).

    This tool scrapes only essential profile data for quick lookups.
    Performance target: <5 seconds.

    Args:
        linkedin_username (str): LinkedIn username (e.g., "stickerdaniel", "anistji")

    Returns:
        Dict[str, Any]: Basic profile data including name, headline, location, about, and current company
    """
    try:
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.error_handler import safe_get_session

        # Construct clean LinkedIn URL from username
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_username}/"

        # Get authenticated session
        session = await safe_get_session()

        logger.info(f"Scraping minimal profile: {linkedin_url}")

        # Use MINIMAL fields for fast scraping (~2-5 seconds)
        person = await session.get_profile(
            linkedin_url, fields=PersonScrapingFields.MINIMAL
        )

        # Convert Pydantic model to dict
        result = person.model_dump()

        # Transform to simplified format for minimal response
        return {
            "name": result.get("name"),
            "headline": result.get("headline"),
            "location": result.get("location"),
            "about": result.get("about", []),
            "company": result.get("company"),
            "job_title": result.get(
                "headline"
            ),  # Map headline to job_title for compatibility
            "open_to_work": result.get("open_to_work", False),
            "scraping_mode": "minimal",
        }

    except Exception as e:
        return handle_tool_error(e, "get_person_profile_minimal")


async def get_person_profile(linkedin_username: str) -> Dict[str, Any]:
    """
    Get a comprehensive person's LinkedIn profile with all available data.

    This tool scrapes complete profile information including experience, education,
    interests, accomplishments, and contacts. Maintains exact compatibility with
    existing output format. Performance target: <35 seconds.

    Args:
        linkedin_username (str): LinkedIn username (e.g., "stickerdaniel", "anistji")

    Returns:
        Dict[str, Any]: Complete structured profile data matching testdata/testscrape.txt format
    """
    try:
        from linkedin_mcp_server.scraper.config import PersonScrapingFields
        from linkedin_mcp_server.error_handler import safe_get_session

        # Construct clean LinkedIn URL from username
        linkedin_url = f"https://www.linkedin.com/in/{linkedin_username}/"

        # Get authenticated session
        session = await safe_get_session()

        logger.info(f"Scraping comprehensive profile: {linkedin_url}")

        # Use ALL fields for comprehensive scraping (~30 seconds)
        person = await session.get_profile(
            linkedin_url, fields=PersonScrapingFields.ALL
        )

        # Convert Pydantic model to dict
        result = person.model_dump()

        # Transform experiences to match exact testdata format
        experiences: List[Dict[str, Any]] = []
        for exp in result.get("experiences", []):
            experiences.append(
                {
                    "position_title": exp.get("position_title", ""),
                    "company": exp.get(
                        "institution_name", ""
                    ),  # Map institution_name to company
                    "from_date": exp.get("from_date", ""),
                    "to_date": exp.get("to_date", ""),
                    "duration": exp.get("duration", ""),
                    "location": exp.get("location", ""),
                    "description": exp.get("description", ""),
                }
            )

        # Transform educations to match exact testdata format
        educations: List[Dict[str, Any]] = []
        for edu in result.get("educations", []):
            educations.append(
                {
                    "institution": edu.get(
                        "institution_name", ""
                    ),  # Map institution_name to institution
                    "degree": edu.get("degree", ""),
                    "from_date": edu.get("from_date"),
                    "to_date": edu.get("to_date"),
                    "description": edu.get("description", ""),
                }
            )

        # Transform interests to match testdata format (list of strings)
        interests: List[str] = []
        for interest in result.get("interests", []):
            if isinstance(interest, dict):
                interests.append(interest.get("name", str(interest)))
            else:
                interests.append(str(interest))

        # Transform accomplishments - combine honors and languages
        accomplishments: List[Dict[str, str]] = []

        # Add honors
        for honor in result.get("honors", []):
            accomplishments.append(
                {"category": "Honor", "title": honor.get("title", "")}
            )

        # Add languages
        for language in result.get("languages", []):
            accomplishments.append(
                {"category": "Language", "title": language.get("name", "")}
            )

        # Transform contacts/connections
        contacts: List[Dict[str, str]] = []
        for contact in result.get("connections", []):
            contacts.append(
                {
                    "name": contact.get("name", ""),
                    "occupation": contact.get("occupation", ""),
                    "url": contact.get("url", ""),
                }
            )

        # Return in exact testdata/testscrape.txt format
        return {
            "name": result.get("name"),
            "about": result.get("about")
            if result.get("about")
            else None,  # Match null format from testdata
            "experiences": experiences,
            "educations": educations,
            "interests": interests,
            "accomplishments": accomplishments,
            "contacts": contacts,
            "company": result.get("company"),
            "job_title": result.get(
                "headline"
            ),  # Map headline to job_title for compatibility
            "open_to_work": result.get("open_to_work", False),
        }

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
