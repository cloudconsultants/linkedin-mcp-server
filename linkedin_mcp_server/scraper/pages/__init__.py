"""Unified page scrapers using centralized stealth architecture.

This module contains page-based scrapers that replace the scattered
section-based approach with unified, high-performance scraping.
"""

from linkedin_mcp_server.scraper.pages.base import LinkedInPageScraper
from linkedin_mcp_server.scraper.pages.profile_page import ProfilePageScraper

__all__ = [
    "LinkedInPageScraper",
    "ProfilePageScraper",
]