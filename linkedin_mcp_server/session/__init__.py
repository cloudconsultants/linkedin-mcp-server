# linkedin_mcp_server/session/__init__.py
"""
Session management module for Playwright-based LinkedIn scraping.

Provides singleton session management with persistent authentication across
multiple tool calls, automatic cleanup, and thread-safe session creation.
"""

from .manager import PlaywrightSessionManager

__all__ = ["PlaywrightSessionManager"]
