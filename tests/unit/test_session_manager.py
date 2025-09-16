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
        session = await PlaywrightSessionManager.create_session("valid_cookie_123")

        assert session is not None
        mock_linkedin_session_class.from_cookie.assert_called_once_with(
            "valid_cookie_123", headless=True
        )

    async def test_get_or_create_session_delegates_to_create(self, mock_linkedin_session_class):
        """Test that get_or_create_session delegates to create_session"""
        session = await PlaywrightSessionManager.get_or_create_session(
            "valid_cookie_123", headless=False
        )

        assert session is not None
        mock_linkedin_session_class.from_cookie.assert_called_once_with(
            "valid_cookie_123", headless=False
        )

    async def test_session_creation_failure(self, mock_linkedin_session_class):
        """Test handling of session creation failures"""
        mock_linkedin_session_class.from_cookie.side_effect = Exception("Creation failed")

        with pytest.raises(Exception, match="Creation failed"):
            await PlaywrightSessionManager.create_session("invalid_cookie")

    def test_has_active_session_always_false(self):
        """Test that has_active_session always returns False in simplified manager"""
        assert not PlaywrightSessionManager.has_active_session()

    async def test_get_active_session_always_none(self):
        """Test that get_active_session always returns None in simplified manager"""
        session = await PlaywrightSessionManager.get_active_session()
        assert session is None

    async def test_close_all_sessions_no_op(self):
        """Test that close_all_sessions is a no-op in simplified manager"""
        # Should not raise any exceptions
        await PlaywrightSessionManager.close_all_sessions()

    def test_get_storage_state_path(self):
        """Test storage state path generation"""
        path = PlaywrightSessionManager._get_storage_state_path("test_session")
        assert "session_test_session.json" in path
        assert ".cache/linkedin-mcp-server" in path
