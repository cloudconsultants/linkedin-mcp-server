# src/linkedin_mcp_server/tools/company.py
"""
LinkedIn company profile scraping tools with employee data extraction.

Provides MCP tools for extracting company information, employee lists, and company
insights from LinkedIn with configurable depth and comprehensive error handling.
"""

import logging
from typing import Any, Dict

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_company_tools(mcp: FastMCP) -> None:
    """
    Register company-related tools with the MCP server.

    Note: Company tools are temporarily unavailable during Playwright migration.
    Will be reimplemented in a future release.

    Args:
        mcp (FastMCP): The MCP server instance
    """

    @mcp.tool()
    async def get_company_profile(
        company_name: str, get_employees: bool = False
    ) -> Dict[str, Any]:
        """
        Get a specific company's LinkedIn profile.

        Args:
            company_name (str): LinkedIn company name (e.g., "docker", "anthropic", "microsoft")
            get_employees (bool): Whether to scrape the company's employees (slower)

        Returns:
            Dict[str, Any]: Error response indicating feature not available
        """
        logger.warning(
            "Company profile scraping temporarily unavailable during Playwright migration"
        )
        return {
            "error": "feature_not_available",
            "message": "Company profile scraping is temporarily unavailable during migration to Playwright",
            "resolution": "Use person profile tools instead, or wait for future release with company support",
            "requested_company": company_name,
            "status": "migration_in_progress",
        }
