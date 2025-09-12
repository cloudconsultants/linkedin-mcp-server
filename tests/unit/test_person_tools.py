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
            "open_to_work": False,
        }
        return person

    @pytest.fixture
    def mock_person_full(self):
        """Mock Person object for full scraping with testdata-like structure"""
        person = Mock()
        person.model_dump.return_value = {
            "name": "Test User",
            "headline": "Software Developer",
            "about": ["Full stack developer with 5 years experience"],
            "company": "Tech Corp",
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
                    "institution_name": "University of California",
                    "degree": "Bachelor of Science in Computer Science",
                    "from_date": "2015",
                    "to_date": "2019",
                    "description": "Computer Science with focus on web technologies",
                }
            ],
            "interests": [{"name": "Machine Learning"}, {"name": "Web Development"}],
            "honors": [{"title": "Dean's List"}],
            "languages": [{"name": "English"}, {"name": "Spanish"}],
            "connections": [
                {
                    "name": "John Doe",
                    "occupation": "Product Manager",
                    "url": "https://linkedin.com/in/johndoe",
                }
            ],
            "open_to_work": False,
        }
        return person

    @pytest.mark.asyncio
    async def test_minimal_profile_success(self, mock_person_minimal):
        """Test successful minimal profile scraping"""
        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get_profile.return_value = mock_person_minimal
            mock_get_session.return_value = mock_session

            result = await get_person_profile_minimal("testuser")

            # Verify correct PersonScrapingFields.MINIMAL was used
            mock_session.get_profile.assert_called_once()
            call_args = mock_session.get_profile.call_args
            assert "https://www.linkedin.com/in/testuser/" in str(call_args)

            # Verify response format
            assert result["name"] == "Test User"
            assert result["headline"] == "Software Developer"
            assert result["location"] == "San Francisco, CA"
            assert result["scraping_mode"] == "minimal"
            assert (
                result["job_title"] == "Software Developer"
            )  # headline mapped to job_title
            assert "about" in result
            assert "company" in result
            assert "open_to_work" in result

    @pytest.mark.asyncio
    async def test_full_profile_success(self, mock_person_full):
        """Test successful comprehensive profile scraping"""
        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get_profile.return_value = mock_person_full
            mock_get_session.return_value = mock_session

            result = await get_person_profile("testuser")

            # Verify correct PersonScrapingFields.ALL was used
            mock_session.get_profile.assert_called_once()
            call_args = mock_session.get_profile.call_args
            assert "https://www.linkedin.com/in/testuser/" in str(call_args)

            # Verify comprehensive response structure
            assert result["name"] == "Test User"
            assert result["job_title"] == "Software Developer"  # headline mapped
            assert result["company"] == "Tech Corp"
            assert result["about"] == ["Full stack developer with 5 years experience"]
            assert not result["open_to_work"]

            # Verify experiences transformation (institution_name -> company)
            assert len(result["experiences"]) == 1
            exp = result["experiences"][0]
            assert exp["position_title"] == "Senior Software Developer"
            assert exp["company"] == "Tech Corp Inc"  # Mapped from institution_name
            assert exp["from_date"] == "Jan 2020"
            assert exp["to_date"] == "Present"

            # Verify educations transformation (institution_name -> institution)
            assert len(result["educations"]) == 1
            edu = result["educations"][0]
            assert (
                edu["institution"] == "University of California"
            )  # Mapped from institution_name
            assert edu["degree"] == "Bachelor of Science in Computer Science"

            # Verify interests transformation (extract names)
            assert len(result["interests"]) == 2
            assert "Machine Learning" in result["interests"]
            assert "Web Development" in result["interests"]

            # Verify accomplishments transformation (honors + languages)
            accomplishments = result["accomplishments"]
            assert len(accomplishments) == 3  # 1 honor + 2 languages

            honor_titles = [
                acc["title"] for acc in accomplishments if acc["category"] == "Honor"
            ]
            language_titles = [
                acc["title"] for acc in accomplishments if acc["category"] == "Language"
            ]

            assert "Dean's List" in honor_titles
            assert "English" in language_titles
            assert "Spanish" in language_titles

            # Verify contacts
            assert len(result["contacts"]) == 1
            contact = result["contacts"][0]
            assert contact["name"] == "John Doe"
            assert contact["occupation"] == "Product Manager"

    @pytest.mark.asyncio
    async def test_minimal_profile_error_handling(self):
        """Test error handling in minimal profile tool"""
        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_get_session.side_effect = Exception("Session failed")

            result = await get_person_profile_minimal("testuser")

            # Should return error dict, not raise exception
            assert isinstance(result, dict)
            assert "error" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_full_profile_error_handling(self):
        """Test error handling in full profile tool"""
        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_get_session.side_effect = Exception("Session failed")

            result = await get_person_profile("testuser")

            # Should return error dict, not raise exception
            assert isinstance(result, dict)
            assert "error" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_username_to_url_conversion(self, mock_person_minimal):
        """Test that usernames are correctly converted to LinkedIn URLs"""
        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get_profile.return_value = mock_person_minimal
            mock_get_session.return_value = mock_session

            await get_person_profile_minimal("john-doe-123")

            # Verify URL construction
            call_args = mock_session.get_profile.call_args[0]
            assert call_args[0] == "https://www.linkedin.com/in/john-doe-123/"

    @pytest.mark.asyncio
    async def test_data_transformation_edge_cases(self):
        """Test data transformation with missing/null fields"""
        person = Mock()
        person.model_dump.return_value = {
            "name": "Edge Case User",
            "headline": None,  # Test null headline
            "about": None,  # Test null about
            "company": "",  # Test empty company
            "experiences": [],  # Test empty experiences
            "educations": [],  # Test empty educations
            "interests": [],  # Test empty interests
            "honors": [],  # Test empty honors
            "languages": [],  # Test empty languages
            "connections": [],  # Test empty connections
            "open_to_work": None,  # Test null open_to_work
        }

        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get_profile.return_value = person
            mock_get_session.return_value = mock_session

            # Test minimal profile with edge cases
            minimal_result = await get_person_profile_minimal("edgecase")

            assert minimal_result["name"] == "Edge Case User"
            assert minimal_result["headline"] is None
            assert minimal_result["job_title"] is None  # Should map from null headline
            assert minimal_result["company"] == ""
            assert minimal_result["about"] is None
            assert minimal_result["open_to_work"] is None

            # Test full profile with edge cases
            full_result = await get_person_profile("edgecase")

            assert full_result["name"] == "Edge Case User"
            assert full_result["about"] is None  # Should preserve null
            assert full_result["experiences"] == []
            assert full_result["educations"] == []
            assert full_result["interests"] == []
            assert full_result["accomplishments"] == []
            assert full_result["contacts"] == []
            assert full_result["open_to_work"] is None

    @pytest.mark.asyncio
    async def test_interests_string_handling(self):
        """Test interests can handle both dict and string formats"""
        person = Mock()
        person.model_dump.return_value = {
            "name": "Interest Test",
            "headline": "Test",
            "about": [],
            "company": "Test",
            "experiences": [],
            "educations": [],
            "interests": [
                {"name": "Programming"},  # Dict format
                "Design",  # String format
                {"name": "Music", "type": "hobby"},  # Dict with extra fields
            ],
            "honors": [],
            "languages": [],
            "connections": [],
            "open_to_work": False,
        }

        with patch(
            "linkedin_mcp_server.error_handler.safe_get_session"
        ) as mock_get_session:
            mock_session = AsyncMock()
            mock_session.get_profile.return_value = person
            mock_get_session.return_value = mock_session

            result = await get_person_profile("interesttest")

            interests = result["interests"]
            assert len(interests) == 3
            assert "Programming" in interests
            assert "Design" in interests
            assert "Music" in interests
