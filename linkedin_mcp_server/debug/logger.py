"""Enhanced debugging system for LinkedIn MCP Server session management."""

import logging
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Dict, Any, Set, Optional


class DebugLevel(Enum):
    BASIC = "BASIC"
    ENHANCED = "ENHANCED"
    TRACE = "TRACE"


class DebugCategory(Enum):
    SESSION = "session"
    COOKIE = "cookie"
    BROWSER = "browser"
    LINKEDIN = "linkedin"
    AUTH = "auth"
    ALL = "all"


class SessionDebugLogger:
    """Enhanced logger for session lifecycle debugging."""

    def __init__(
        self,
        level: DebugLevel = DebugLevel.BASIC,
        categories: Optional[Set[DebugCategory]] = None,
    ):
        self.level = level
        self.categories = categories or {DebugCategory.SESSION}
        self.logger = logging.getLogger("linkedin_mcp.debug")
        self._session_timings = {}

    def should_log_category(self, category: DebugCategory) -> bool:
        """Check if category should be logged."""
        return category in self.categories or DebugCategory.ALL in self.categories

    def log_session_event(
        self,
        event: str,
        session_id: str = "default",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log session lifecycle events with timing."""
        if not self.should_log_category(DebugCategory.SESSION):
            return

        timestamp = time.time()
        self._session_timings[f"{session_id}_{event}"] = timestamp
        self.logger.info(f"[SESSION] {event} - {session_id}", extra=extra or {})

    def log_cookie_event(
        self,
        event: str,
        cookie_status: Optional[str] = None,
        expires_in: Optional[str] = None,
    ):
        """Log cookie management events."""
        if not self.should_log_category(DebugCategory.COOKIE):
            return

        extra_info = f" - Status: {cookie_status}" if cookie_status else ""
        extra_info += f" - Expires: {expires_in}" if expires_in else ""
        self.logger.info(f"[COOKIE] {event}{extra_info}")

    def log_storage_event(self, event: str, path: Optional[str] = None):
        """Log storage state events."""
        if not self.should_log_category(DebugCategory.SESSION):
            return

        path_info = f" - {path}" if path else ""
        self.logger.info(f"[STORAGE] {event}{path_info}")

    @asynccontextmanager
    async def session_lifecycle_tracker(self, session_id: str = "default"):
        """Context manager to track complete session lifecycle."""
        self.log_session_event("CREATING", session_id)
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time
            self.log_session_event(
                "CREATED_SUCCESS", session_id, {"duration_seconds": round(duration, 2)}
            )
        except Exception as e:
            duration = time.time() - start_time
            self.log_session_event(
                "CREATED_FAILED",
                session_id,
                {"duration_seconds": round(duration, 2), "error": str(e)},
            )
            raise


# Global debug logger instance
debug_logger: Optional[SessionDebugLogger] = None


def init_debug_logger(level: str = "BASIC", categories: str = "session"):
    """Initialize global debug logger."""
    global debug_logger

    level_enum = DebugLevel(level.upper()) if level else DebugLevel.BASIC

    # Parse categories
    category_set = set()
    if categories:
        for cat in categories.lower().split(","):
            cat = cat.strip()
            if cat == "all":
                category_set.add(DebugCategory.ALL)
            else:
                try:
                    category_set.add(DebugCategory(cat))
                except ValueError:
                    logging.warning(f"Unknown debug category: {cat}")

    if not category_set:
        category_set.add(DebugCategory.SESSION)

    debug_logger = SessionDebugLogger(level_enum, category_set)


def get_debug_logger() -> SessionDebugLogger:
    """Get the global debug logger."""
    global debug_logger
    if debug_logger is None:
        init_debug_logger()
    if debug_logger is None:
        # Fallback initialization if init_debug_logger() failed
        debug_logger = SessionDebugLogger(DebugLevel.BASIC, {"session"})
    return debug_logger
