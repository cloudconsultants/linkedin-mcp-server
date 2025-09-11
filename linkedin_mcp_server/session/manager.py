# linkedin_mcp_server/session/manager.py
"""
Playwright session manager with singleton pattern for LinkedIn scraping.

Provides persistent LinkedIn sessions across multiple tool calls with proper
cleanup, thread-safe session creation, and authentication management.
"""

import asyncio
import logging
from typing import Dict, Optional

from linkedin_mcp_server.scraper.session import LinkedInSession

logger = logging.getLogger(__name__)


class PlaywrightSessionManager:
    """
    Singleton session manager with persistent authentication for multiple tool calls.

    Manages LinkedIn sessions using Playwright with automatic context management,
    thread-safe session creation, and proper cleanup handling.
    """

    _sessions: Dict[str, LinkedInSession] = {}
    _session_locks: Dict[str, asyncio.Lock] = {}
    _initialized = False

    @classmethod
    async def get_or_create_session(
        cls, authentication: str, headless: bool = True
    ) -> LinkedInSession:
        """
        Get existing session or create a new one with authentication.

        Args:
            authentication: LinkedIn session cookie (li_at=value format)
            headless: Whether to run browser in headless mode

        Returns:
            LinkedInSession: Active authenticated session

        Raises:
            Exception: If session creation or authentication fails
        """
        session_id = "default"  # Single persistent session

        # Create lock if it doesn't exist
        if session_id not in cls._session_locks:
            cls._session_locks[session_id] = asyncio.Lock()

        async with cls._session_locks[session_id]:
            # Return existing session if available and authenticated
            if session_id in cls._sessions:
                session = cls._sessions[session_id]
                try:
                    # Check if session is still valid
                    if (
                        hasattr(session, "is_authenticated")
                        and await session.is_authenticated()
                    ):
                        logger.info("Using existing authenticated LinkedIn session")
                        return session
                    else:
                        logger.info(
                            "Existing session not authenticated, creating new one"
                        )
                        # Clean up old session
                        try:
                            await session.close()
                        except Exception as e:
                            logger.warning(f"Error closing old session: {e}")
                        del cls._sessions[session_id]
                except Exception as e:
                    logger.warning(f"Error checking session authentication: {e}")
                    # Clean up problematic session
                    try:
                        await session.close()
                    except Exception:
                        pass
                    del cls._sessions[session_id]

            # Create new session
            try:
                logger.info("Creating new LinkedIn session with Playwright...")
                session = LinkedInSession.from_cookie(authentication, headless=headless)

                # Enter the context manager manually to keep session alive
                await session.__aenter__()

                # Store the session
                cls._sessions[session_id] = session
                logger.info("Created and authenticated new persistent LinkedIn session")

                return session

            except Exception as e:
                logger.error(f"Failed to create LinkedIn session: {e}")
                # Clean up failed session if it was stored
                if session_id in cls._sessions:
                    try:
                        await cls._sessions[session_id].close()
                    except Exception:
                        pass
                    del cls._sessions[session_id]
                raise e

    @classmethod
    async def close_all_sessions(cls) -> None:
        """Close all active sessions and clean up resources."""
        if not cls._sessions:
            logger.info("No sessions to close")
            return

        logger.info(f"Closing {len(cls._sessions)} LinkedIn sessions...")

        for session_id, session in list(cls._sessions.items()):
            try:
                logger.info(f"Closing session {session_id}")
                await session.close()
                logger.info(f"Successfully closed session {session_id}")
            except Exception as e:
                logger.warning(f"Error closing session {session_id}: {e}")

        # Clear all sessions and locks
        cls._sessions.clear()
        cls._session_locks.clear()
        cls._initialized = False
        logger.info("All LinkedIn sessions closed and cleaned up")

    @classmethod
    async def get_active_session(cls) -> Optional[LinkedInSession]:
        """
        Get the currently active session without creating a new one.

        Returns:
            Optional[LinkedInSession]: Active session if available, None otherwise
        """
        session_id = "default"
        return cls._sessions.get(session_id)

    @classmethod
    def has_active_session(cls) -> bool:
        """
        Check if there is an active session.

        Returns:
            bool: True if there is an active session, False otherwise
        """
        session_id = "default"
        return session_id in cls._sessions
