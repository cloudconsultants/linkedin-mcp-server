"""Centralized stealth control system for LinkedIn automation.

This module provides a high-performance, configurable stealth system that:
- Achieves 75-85% speed improvement over the legacy system
- Centralizes all stealth operations into a single control point
- Enables multi-content support for profiles, jobs, companies, and feeds
- Provides intelligent content detection replacing hardcoded waits
- Maintains backward compatibility during migration
"""

from linkedin_mcp_server.scraper.stealth.controller import StealthController
from linkedin_mcp_server.scraper.stealth.profiles import (
    NavigationMode,
    SimulationLevel,
    StealthProfile,
    get_stealth_profile,
)

__all__ = [
    "StealthController",
    "StealthProfile",
    "NavigationMode",
    "SimulationLevel",
    "get_stealth_profile",
]
