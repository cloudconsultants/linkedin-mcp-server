# linkedin_mcp_server/session/manager.py
"""
Playwright session manager with singleton pattern for LinkedIn scraping.

Provides persistent LinkedIn sessions across multiple tool calls with proper
cleanup, thread-safe session creation, and authentication management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from linkedin_mcp_server.scraper.session import LinkedInSession
from linkedin_mcp_server.debug import get_debug_logger

logger = logging.getLogger(__name__)


class PlaywrightSessionManager:
    """
    Simplified session manager without singleton pattern to avoid asyncio conflicts.

    Creates sessions on-demand within the MCP server's event loop context,
    avoiding cross-loop asyncio conflicts that cause TaskGroup errors.
    """

    @classmethod
    def _get_storage_state_path(cls, session_id: str = "default") -> str:
        """Get storage state file path for session."""
        # Store in user's cache directory or temp
        cache_dir = Path.home() / ".cache" / "linkedin-mcp-server"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / f"session_{session_id}.json")

    @classmethod
    async def create_session(
        cls, authentication: str, headless: bool = True
    ) -> LinkedInSession:
        """
        Create a new session without singleton storage to avoid asyncio conflicts.

        Args:
            authentication: LinkedIn session cookie (li_at=value format)
            headless: Whether to run browser in headless mode

        Returns:
            LinkedInSession: New authenticated session

        Raises:
            Exception: If session creation or authentication fails
        """
        debug_logger = get_debug_logger()

        try:
            logger.info("Creating new LinkedIn session...")
            debug_logger.log_session_event("CREATING_NEW", "temp")

            # Create session (no singleton storage to avoid asyncio conflicts)
            session = LinkedInSession.from_cookie(authentication, headless=headless)
            await session.__aenter__()

            logger.info("Created and authenticated new LinkedIn session")
            return session

        except Exception as e:
            logger.error(f"Failed to create LinkedIn session: {e}")
            debug_logger.log_session_event("CREATION_FAILED", "temp", {"error": str(e)})
            raise e

    @classmethod
    async def get_or_create_session(
        cls, authentication: str, headless: bool = True
    ) -> LinkedInSession:
        """
        Backward compatibility method - delegates to create_session.
        
        Args:
            authentication: LinkedIn session cookie (li_at=value format)
            headless: Whether to run browser in headless mode

        Returns:
            LinkedInSession: New authenticated session

        Raises:
            Exception: If session creation or authentication fails
        """
        return await cls.create_session(authentication, headless)

    @classmethod
    async def close_all_sessions(cls) -> None:
        """Placeholder for backward compatibility - no sessions to close."""
        logger.info("No persistent sessions to close (using on-demand sessions)")

    @classmethod
    async def get_active_session(cls) -> Optional[LinkedInSession]:
        """
        No active sessions in simplified manager.

        Returns:
            None: Always returns None since we don't store sessions
        """
        return None

    @classmethod
    def has_active_session(cls) -> bool:
        """
        No active sessions in simplified manager.

        Returns:
            False: Always returns False since we don't store sessions
        """
        return False
