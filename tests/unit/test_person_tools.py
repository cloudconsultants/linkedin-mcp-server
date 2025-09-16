# tests/unit/test_person_tools.py
"""
Unit tests for person profile tools.

Tests tool logic, data transformation, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from linkedin_mcp_server.tools.person import (
    get_person_profile,
    get_person_profile_minimal,
)


class TestPersonTools:
    @pytest.fixture
    def mock_person_minimal(self):
        """Mock Person object for minimal scraping"""
        person = Mock()
        person.model_dump.return_value = {
            "name": "Test User",
            "headline": "Software Developer",
            "location": "San Francisco, CA",
            "about": ["Passionate developer"],
            "company": "Tech Corp",
            "linkedin_url": "https://www.linkedin.com/in/testuser/",
            "connection_count": 500,
            "followers_count": 1200,
            "website_url": "https://testuser.dev",
            "open_to_work": False,
            "experiences": [],
            "educations": [],
            "interests": [],
            "languages": [],
            "honors": [],
            "connections": [],
        }
        return person

    @pytest.fixture
    def mock_person_full(self):
        """Mock Person object for comprehensive scraping"""
        person = Mock()
        person.model_dump.return_value = {
            "name": "Test User",
            "headline": "Senior Software Developer",
            "about": ["Full stack developer with 5 years experience"],
            "company": "Tech Corp",
            "linkedin_url": "https://www.linkedin.com/in/testuser/",
            "connection_count": 500,
            "followers_count": 1200,
            "website_url": "https://testuser.dev",
            "experiences": [
                {
                    "position_title": "Senior Software Developer",
                    "institution_name": "Tech Corp Inc",
                    "from_date": "Jan 2020",
                    "to_date": "Present",
                    "duration": "4 yrs",
                    "location": "San Francisco, CA",
                    "description": "Full stack development using React and Node.js",
                }
            ],
            "educations": [
                {
                    "institution_name": "University of Technology",
                    "field_of_study": "Computer Science",
                    "degree": "Bachelor's",
                    "from_date": "2015",
                    "to_date": "2019",
                }
            ],
            "interests": ["Programming", "Machine Learning", "Open Source"],
            "languages": ["English", "Spanish"],
            "honors": [],
            "connections": [],
            "open_to_work": False,
        }
        return person

    @pytest.mark.asyncio
    async def test_minimal_profile_success(self, mock_person_minimal):
        """Test successful minimal profile scraping with new direct Playwright approach"""
        with patch.dict("os.environ", {"LINKEDIN_COOKIE": "test_cookie_value"}):
            with patch("patchright.async_api.async_playwright") as mock_playwright:
                # Mock Playwright components properly
                mock_playwright_instance = AsyncMock()
                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                # Set up the async playwright chain properly
                mock_playwright.return_value = mock_playwright_instance
                mock_playwright_instance.start = AsyncMock(return_value=mock_playwright_instance)
                mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.add_cookies = AsyncMock()
                mock_browser.close = AsyncMock()
                mock_playwright_instance.stop = AsyncMock()

                # Mock ProfilePageScraper
                with patch("linkedin_mcp_server.scraper.pages.profile_page.ProfilePageScraper") as mock_scraper_class:
                    mock_scraper = AsyncMock()
                    mock_scraper_class.return_value = mock_scraper
                    mock_scraper.scrape_page = AsyncMock(return_value=mock_person_minimal)

                    result = await get_person_profile_minimal("testuser")

                    # Verify ProfilePageScraper was called correctly
                    mock_scraper_class.assert_called_once()
                    mock_scraper.scrape_page.assert_called_once()
                    
                    # Verify result contains raw model data plus performance metrics
                    assert result["name"] == "Test User"
                    assert result["headline"] == "Software Developer"
                    assert result["linkedin_url"] == "https://www.linkedin.com/in/testuser/"
                    assert result["connection_count"] == 500
                    assert result["followers_count"] == 1200
                    assert result["website_url"] == "https://testuser.dev"
                    assert "_performance" in result
                    assert result["_performance"]["scraping_mode"] == "minimal"
                    assert result["_performance"]["stealth_profile"] == "NO_STEALTH"

    @pytest.mark.asyncio
    async def test_full_profile_success(self, mock_person_full):
        """Test successful comprehensive profile scraping with new direct Playwright approach"""
        with patch.dict("os.environ", {"LINKEDIN_COOKIE": "test_cookie_value"}):
            with patch("patchright.async_api.async_playwright") as mock_playwright:
                # Mock Playwright components properly
                mock_playwright_instance = AsyncMock()
                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                # Set up the async playwright chain properly
                mock_playwright.return_value = mock_playwright_instance
                mock_playwright_instance.start = AsyncMock(return_value=mock_playwright_instance)
                mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.add_cookies = AsyncMock()
                mock_browser.close = AsyncMock()
                mock_playwright_instance.stop = AsyncMock()

                # Mock ProfilePageScraper
                with patch("linkedin_mcp_server.scraper.pages.profile_page.ProfilePageScraper") as mock_scraper_class:
                    mock_scraper = AsyncMock()
                    mock_scraper_class.return_value = mock_scraper
                    mock_scraper.scrape_page = AsyncMock(return_value=mock_person_full)

                    result = await get_person_profile("testuser")

                    # Verify ProfilePageScraper was called correctly
                    mock_scraper_class.assert_called_once()
                    mock_scraper.scrape_page.assert_called_once()
                    
                    # Verify comprehensive result structure
                    assert result["name"] == "Test User"
                    assert result["headline"] == "Senior Software Developer"
                    assert result["linkedin_url"] == "https://www.linkedin.com/in/testuser/"
                    assert len(result["experiences"]) == 1
                    assert len(result["educations"]) == 1
                    assert len(result["interests"]) == 3
                    assert result["interests"] == ["Programming", "Machine Learning", "Open Source"]
                    assert "_performance" in result
                    assert result["_performance"]["scraping_mode"] == "comprehensive"

    @pytest.mark.asyncio
    async def test_minimal_profile_error_handling(self):
        """Test error handling when LINKEDIN_COOKIE is not set"""
        with patch.dict("os.environ", {}, clear=True):  # Clear environment variables
            result = await get_person_profile_minimal("testuser")
            
            # Should return error structure from handle_tool_error
            assert result["error"] == "unknown_error"
            assert "LINKEDIN_COOKIE environment variable not set" in result["message"]

    @pytest.mark.asyncio
    async def test_full_profile_error_handling(self):
        """Test error handling when LINKEDIN_COOKIE is not set"""
        with patch.dict("os.environ", {}, clear=True):  # Clear environment variables
            result = await get_person_profile("testuser")
            
            # Should return error structure from handle_tool_error
            assert result["error"] == "unknown_error"
            assert "LINKEDIN_COOKIE environment variable not set" in result["message"]

    @pytest.mark.asyncio
    async def test_username_to_url_conversion(self, mock_person_minimal):
        """Test that username is correctly converted to LinkedIn URL"""
        with patch.dict("os.environ", {"LINKEDIN_COOKIE": "test_cookie_value"}):
            with patch("patchright.async_api.async_playwright") as mock_playwright:
                # Mock Playwright components properly
                mock_playwright_instance = AsyncMock()
                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                # Set up the async playwright chain properly
                mock_playwright.return_value = mock_playwright_instance
                mock_playwright_instance.start = AsyncMock(return_value=mock_playwright_instance)
                mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.add_cookies = AsyncMock()
                mock_browser.close = AsyncMock()
                mock_playwright_instance.stop = AsyncMock()

                with patch("linkedin_mcp_server.scraper.pages.profile_page.ProfilePageScraper") as mock_scraper_class:
                    mock_scraper = AsyncMock()
                    mock_scraper_class.return_value = mock_scraper
                    mock_scraper.scrape_page = AsyncMock(return_value=mock_person_minimal)

                    await get_person_profile_minimal("john-doe")

                    # Verify the URL was constructed correctly
                    call_args = mock_scraper.scrape_page.call_args
                    url_arg = call_args[0][1]  # Second positional argument
                    assert url_arg == "https://www.linkedin.com/in/john-doe/"

    @pytest.mark.asyncio 
    async def test_browser_cleanup_handling(self, mock_person_minimal):
        """Test that browser cleanup errors are handled gracefully"""
        with patch.dict("os.environ", {"LINKEDIN_COOKIE": "test_cookie_value"}):
            with patch("patchright.async_api.async_playwright") as mock_playwright:
                # Mock Playwright components with cleanup errors
                mock_playwright_instance = AsyncMock()
                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                # Set up the async playwright chain properly
                mock_playwright.return_value = mock_playwright_instance
                mock_playwright_instance.start = AsyncMock(return_value=mock_playwright_instance)
                mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.add_cookies = AsyncMock()

                # Make browser.close() raise an exception
                mock_browser.close = AsyncMock(side_effect=Exception("Browser close error"))
                mock_playwright_instance.stop = AsyncMock(side_effect=Exception("Playwright stop error"))

                with patch("linkedin_mcp_server.scraper.pages.profile_page.ProfilePageScraper") as mock_scraper_class:
                    mock_scraper = AsyncMock()
                    mock_scraper_class.return_value = mock_scraper
                    mock_scraper.scrape_page = AsyncMock(return_value=mock_person_minimal)

                    # Should complete successfully despite cleanup errors
                    result = await get_person_profile_minimal("testuser")
                    
                    assert result["name"] == "Test User"
                    assert "_performance" in result
