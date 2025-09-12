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
    Session manager with storage state persistence and debug logging.

    Manages LinkedIn sessions using Playwright with automatic context management,
    thread-safe session creation, storage state persistence, and proper cleanup handling.
    """

    _sessions: Dict[str, LinkedInSession] = {}
    _session_locks: Dict[str, asyncio.Lock] = {}
    _initialized = False

    @classmethod
    def _get_storage_state_path(cls, session_id: str = "default") -> str:
        """Get storage state file path for session."""
        # Store in user's cache directory or temp
        cache_dir = Path.home() / ".cache" / "linkedin-mcp-server"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / f"session_{session_id}.json")

    @classmethod
    async def get_or_create_session(
        cls, authentication: str, headless: bool = True
    ) -> LinkedInSession:
        """
        Get existing session or create a new one with storage state persistence.

        Args:
            authentication: LinkedIn session cookie (li_at=value format)
            headless: Whether to run browser in headless mode

        Returns:
            LinkedInSession: Active authenticated session

        Raises:
            Exception: If session creation or authentication fails
        """
        session_id = "default"  # Single persistent session
        debug_logger = get_debug_logger()

        # Create lock if it doesn't exist
        if session_id not in cls._session_locks:
            cls._session_locks[session_id] = asyncio.Lock()

        async with cls._session_locks[session_id]:
            # Return existing session if available and authenticated
            if session_id in cls._sessions:
                session = cls._sessions[session_id]
                try:
                    debug_logger.log_session_event("VALIDATING_EXISTING", session_id)
                    # Check if session is still valid
                    if (
                        hasattr(session, "is_authenticated")
                        and await session.is_authenticated()  # Now properly async
                    ):
                        logger.info("Using existing authenticated LinkedIn session")
                        debug_logger.log_session_event("REUSING_EXISTING", session_id)
                        return session
                    else:
                        logger.info(
                            "Existing session not authenticated, creating new one"
                        )
                        debug_logger.log_session_event("EXISTING_INVALID", session_id)
                        await cls._cleanup_session(session_id)
                except Exception as e:
                    logger.warning(f"Error checking session authentication: {e}")
                    debug_logger.log_session_event(
                        "VALIDATION_ERROR", session_id, {"error": str(e)}
                    )
                    await cls._cleanup_session(session_id)

            # Create new session with storage state
            try:
                logger.info("Creating new LinkedIn session with storage state...")
                storage_path = cls._get_storage_state_path(session_id)
                debug_logger.log_session_event(
                    "CREATING_NEW", session_id, {"storage_path": storage_path}
                )

                async with debug_logger.session_lifecycle_tracker(session_id):
                    # Create session with storage state support
                    session = LinkedInSession.from_cookie(
                        authentication, headless=headless
                    )
                    # TODO: Pass storage path to session (future enhancement)
                    # if hasattr(session, "_set_storage_state_path"):
                    #     session._set_storage_state_path(storage_path)

                    await session.__aenter__()
                    cls._sessions[session_id] = session

                    debug_logger.log_storage_event("SESSION_STORED", storage_path)
                    logger.info(
                        "Created and authenticated new persistent LinkedIn session"
                    )
                    return session

            except Exception as e:
                logger.error(f"Failed to create LinkedIn session: {e}")
                debug_logger.log_session_event(
                    "CREATION_FAILED", session_id, {"error": str(e)}
                )
                await cls._cleanup_session(session_id)
                raise e

    @classmethod
    async def _cleanup_session(cls, session_id: str):
        """Clean up a specific session with debug logging."""
        debug_logger = get_debug_logger()
        if session_id in cls._sessions:
            try:
                debug_logger.log_session_event("CLEANING_UP", session_id)
                await cls._sessions[session_id].close()
                debug_logger.log_session_event("CLEANUP_SUCCESS", session_id)
            except Exception as e:
                debug_logger.log_session_event(
                    "CLEANUP_ERROR", session_id, {"error": str(e)}
                )
            del cls._sessions[session_id]

    @classmethod
    async def close_all_sessions(cls) -> None:
        """Close all active sessions and clean up resources."""
        debug_logger = get_debug_logger()

        if not cls._sessions:
            logger.info("No sessions to close")
            debug_logger.log_session_event("NO_SESSIONS_TO_CLOSE")
            return

        logger.info(f"Closing {len(cls._sessions)} LinkedIn sessions...")
        debug_logger.log_session_event(
            "CLOSING_ALL_SESSIONS", extra={"count": len(cls._sessions)}
        )

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
        debug_logger.log_session_event("ALL_SESSIONS_CLOSED")

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
