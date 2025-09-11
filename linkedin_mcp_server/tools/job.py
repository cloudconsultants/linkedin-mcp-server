# src/linkedin_mcp_server/tools/job.py
"""
LinkedIn job scraping tools with search and detail extraction capabilities.

Provides MCP tools for job posting details, job searches, and recommendations
with comprehensive filtering and structured data extraction.
"""

import logging
from typing import Any, Dict, List

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_job_tools(mcp: FastMCP) -> None:
    """
    Register job-related tools with the MCP server.
    
    Note: Job tools are temporarily unavailable during Playwright migration.
    Will be reimplemented in a future release.

    Args:
        mcp (FastMCP): The MCP server instance
    """

    @mcp.tool()
    async def get_job_details(job_id: str) -> Dict[str, Any]:
        """
        Get job details for a specific job posting on LinkedIn

        Args:
            job_id (str): LinkedIn job ID (e.g., "4252026496", "3856789012")

        Returns:
            Dict[str, Any]: Error response indicating feature not available
        """
        logger.warning("Job details scraping temporarily unavailable during Playwright migration")
        return {
            "error": "feature_not_available",
            "message": "Job details scraping is temporarily unavailable during migration to Playwright",
            "resolution": "Use person profile tools instead, or wait for future release with job support",
            "requested_job_id": job_id,
            "status": "migration_in_progress"
        }

    @mcp.tool()
    async def search_jobs(search_term: str) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn using a search term.

        Args:
            search_term (str): Search term to use for the job search.

        Returns:
            List[Dict[str, Any]]: Error response indicating feature not available
        """
        logger.warning("Job search temporarily unavailable during Playwright migration")
        return [{
            "error": "feature_not_available",
            "message": "Job search is temporarily unavailable during migration to Playwright",
            "resolution": "Use person profile tools instead, or wait for future release with job support",
            "search_term": search_term,
            "status": "migration_in_progress"
        }]

    @mcp.tool()
    async def get_recommended_jobs() -> List[Dict[str, Any]]:
        """
        Get LinkedIn recommended jobs for the authenticated user.

        Returns:
            List[Dict[str, Any]]: Error response indicating feature not available
        """
        logger.warning("Recommended jobs temporarily unavailable during Playwright migration")
        return [{
            "error": "feature_not_available",
            "message": "Recommended jobs are temporarily unavailable during migration to Playwright",
            "resolution": "Use person profile tools instead, or wait for future release with job support",
            "status": "migration_in_progress"
        }]
