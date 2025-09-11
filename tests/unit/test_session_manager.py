# tests/unit/test_session_manager.py
"""
Unit tests for PlaywrightSessionManager.

Tests session creation, reuse, cleanup, and thread safety.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from linkedin_mcp_server.session.manager import PlaywrightSessionManager


class TestPlaywrightSessionManager:
    @pytest.fixture
    def mock_session(self):
        """Create mock LinkedIn session"""
        session = AsyncMock()
        session.is_authenticated = AsyncMock(return_value=True)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def mock_linkedin_session_class(self, mock_session):
        """Mock LinkedInSession class"""
        with patch("linkedin_mcp_server.session.manager.LinkedInSession") as mock_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_session)
            mock_instance.__aexit__ = AsyncMock()
            mock_class.from_cookie.return_value = mock_instance
            yield mock_class

    async def test_session_creation_success(self, mock_linkedin_session_class):
        """Test successful session creation with valid cookie"""
        # Clear any existing sessions
        PlaywrightSessionManager._sessions.clear()

        session = await PlaywrightSessionManager.get_or_create_session(
            "valid_cookie_123"
        )

        assert session is not None
        mock_linkedin_session_class.from_cookie.assert_called_once_with(
            "valid_cookie_123", headless=True
        )

    async def test_session_reuse(self, mock_linkedin_session_class):
        """Test that same session is reused for multiple calls"""
        PlaywrightSessionManager._sessions.clear()

        session1 = await PlaywrightSessionManager.get_or_create_session("same_cookie")
        session2 = await PlaywrightSessionManager.get_or_create_session("same_cookie")

        assert session1 is session2
        # Should only create session once
        assert mock_linkedin_session_class.from_cookie.call_count == 1

    async def test_concurrent_session_creation(self, mock_linkedin_session_class):
        """Test thread-safe concurrent session creation"""
        PlaywrightSessionManager._sessions.clear()

        # Simulate multiple concurrent calls
        tasks = [
            PlaywrightSessionManager.get_or_create_session("concurrent_cookie")
            for _ in range(5)
        ]

        sessions = await asyncio.gather(*tasks)

        # All should return same session instance
        assert all(s is sessions[0] for s in sessions)
        # Should only create session once despite concurrent calls
        assert mock_linkedin_session_class.from_cookie.call_count == 1

    async def test_session_cleanup(self, mock_linkedin_session_class, mock_session):
        """Test proper session cleanup"""
        PlaywrightSessionManager._sessions.clear()

        await PlaywrightSessionManager.get_or_create_session("cleanup_test")
        assert len(PlaywrightSessionManager._sessions) == 1

        await PlaywrightSessionManager.close_all_sessions()

        assert len(PlaywrightSessionManager._sessions) == 0
        assert len(PlaywrightSessionManager._session_locks) == 0
        mock_session.close.assert_called_once()

    async def test_session_creation_failure(self, mock_linkedin_session_class):
        """Test handling of session creation failures"""
        PlaywrightSessionManager._sessions.clear()
        mock_linkedin_session_class.from_cookie.side_effect = Exception(
            "Creation failed"
        )

        with pytest.raises(Exception, match="Creation failed"):
            await PlaywrightSessionManager.get_or_create_session("invalid_cookie")

        # Should not store failed session
        assert len(PlaywrightSessionManager._sessions) == 0

    async def test_invalid_session_recreation(
        self, mock_linkedin_session_class, mock_session
    ):
        """Test recreation of invalid sessions"""
        PlaywrightSessionManager._sessions.clear()

        # Create initial session
        await PlaywrightSessionManager.get_or_create_session("test_cookie")

        # Mock session becoming invalid
        mock_session.is_authenticated = AsyncMock(return_value=False)

        # Should create new session
        await PlaywrightSessionManager.get_or_create_session("test_cookie")

        # Should have called from_cookie twice (initial + recreation)
        assert mock_linkedin_session_class.from_cookie.call_count == 2
        mock_session.close.assert_called_once()  # Old session should be closed

    def test_has_active_session(self):
        """Test session existence checking"""
        PlaywrightSessionManager._sessions.clear()

        assert not PlaywrightSessionManager.has_active_session()

        # Manually add session for testing
        PlaywrightSessionManager._sessions["default"] = Mock()

        assert PlaywrightSessionManager.has_active_session()

        PlaywrightSessionManager._sessions.clear()

    async def test_get_active_session(self):
        """Test getting active session without creating new one"""
        PlaywrightSessionManager._sessions.clear()

        # Should return None when no session exists
        session = await PlaywrightSessionManager.get_active_session()
        assert session is None

        # Add session manually
        mock_session = Mock()
        PlaywrightSessionManager._sessions["default"] = mock_session

        # Should return existing session
        session = await PlaywrightSessionManager.get_active_session()
        assert session is mock_session

        PlaywrightSessionManager._sessions.clear()
