# tests/compatibility/test_migration_compatibility.py
"""
Critical compatibility tests ensuring Playwright migration maintains exact output format.

These tests compare new implementation against testdata/testscrape.txt to ensure
zero breaking changes in MCP tool responses.
"""

import json
import logging
import os
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from linkedin_mcp_server.tools.person import get_person_profile, get_person_profile_minimal

logger = logging.getLogger(__name__)


class TestMigrationCompatibility:
    """Critical tests ensuring migration maintains exact compatibility"""
    
    @pytest.fixture
    def expected_profile_data(self):
        """Load expected profile data from testdata/testscrape.txt"""
        testdata_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "testdata", "testscrape.txt")
        
        if not os.path.exists(testdata_path):
            pytest.skip("testdata/testscrape.txt not found - required for compatibility testing")
        
        with open(testdata_path, "r") as f:
            content = f.read()
            # Extract JSON from the response section
            json_start = content.find('{\n  "name"')
            if json_start == -1:
                pytest.fail("Could not find JSON data in testdata/testscrape.txt")
            
            json_content = content[json_start:]
            return json.loads(json_content)
    
    @pytest.fixture
    def mock_person_data(self, expected_profile_data):
        """Mock Person object that matches expected testdata structure"""
        person = Mock()
        
        # Transform expected data back to what fast-linkedin-scraper would return
        experiences = []
        for exp in expected_profile_data.get("experiences", []):
            experiences.append({
                "position_title": exp.get("position_title", ""),
                "institution_name": exp.get("company", ""),  # Reverse mapping
                "from_date": exp.get("from_date", ""),
                "to_date": exp.get("to_date", ""),
                "duration": exp.get("duration", ""),
                "location": exp.get("location", ""),
                "description": exp.get("description", ""),
            })
        
        educations = []
        for edu in expected_profile_data.get("educations", []):
            educations.append({
                "institution_name": edu.get("institution", ""),  # Reverse mapping
                "degree": edu.get("degree", ""),
                "from_date": edu.get("from_date"),
                "to_date": edu.get("to_date"),
                "description": edu.get("description", ""),
            })
        
        # Mock the model_dump return value
        person.model_dump.return_value = {
            "name": expected_profile_data.get("name"),
            "headline": expected_profile_data.get("job_title"),
            "about": expected_profile_data.get("about"),
            "company": expected_profile_data.get("company"),
            "experiences": experiences,
            "educations": educations,
            "interests": [{"name": interest} for interest in expected_profile_data.get("interests", [])],
            "honors": [{"title": acc.get("title", "")} for acc in expected_profile_data.get("accomplishments", []) if acc.get("category") == "Honor"],
            "languages": [{"name": acc.get("title", "")} for acc in expected_profile_data.get("accomplishments", []) if acc.get("category") == "Language"],
            "connections": expected_profile_data.get("contacts", []),
            "open_to_work": expected_profile_data.get("open_to_work", False),
        }
        
        return person
    
    @pytest.mark.asyncio
    async def test_exact_output_format_match(self, expected_profile_data, mock_person_data):
        """
        CRITICAL TEST: Compare against testdata/testscrape.txt - MUST PASS
        
        This test ensures the new Playwright implementation produces identical
        output to the original Selenium implementation.
        """
        with patch('linkedin_mcp_server.error_handler.safe_get_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.get_profile.return_value = mock_person_data
            mock_session.return_value = mock_session_instance
            
            # Get actual output from new implementation
            result = await get_person_profile("amir-nahvi-94814819")
            
            # CRITICAL: Field-by-field validation
            compatibility_errors = []
            
            # Basic fields comparison
            if result.get("name") != expected_profile_data.get("name"):
                compatibility_errors.append(f"Name mismatch: '{result.get('name')}' != '{expected_profile_data.get('name')}'")
            
            if result.get("about") != expected_profile_data.get("about"):  
                compatibility_errors.append(f"About mismatch: {result.get('about')} != {expected_profile_data.get('about')}")
                
            if result.get("company") != expected_profile_data.get("company"):
                compatibility_errors.append(f"Company mismatch: '{result.get('company')}' != '{expected_profile_data.get('company')}'")
                
            if result.get("job_title") != expected_profile_data.get("job_title"):
                compatibility_errors.append(f"Job title mismatch: '{result.get('job_title')}' != '{expected_profile_data.get('job_title')}'")
                
            if result.get("open_to_work") != expected_profile_data.get("open_to_work"):
                compatibility_errors.append(f"Open to work mismatch: {result.get('open_to_work')} != {expected_profile_data.get('open_to_work')}")
            
            # Experience validation
            result_experiences = result.get("experiences", [])
            expected_experiences = expected_profile_data.get("experiences", [])
            
            if len(result_experiences) != len(expected_experiences):
                compatibility_errors.append(f"Experience count: {len(result_experiences)} != {len(expected_experiences)}")
            
            for i, (new_exp, expected_exp) in enumerate(zip(result_experiences, expected_experiences)):
                for field in ["position_title", "company", "from_date", "to_date", "duration", "location"]:
                    if new_exp.get(field) != expected_exp.get(field):
                        compatibility_errors.append(
                            f"Experience {i} {field}: '{new_exp.get(field)}' != '{expected_exp.get(field)}'"
                        )
            
            # Education validation
            result_educations = result.get("educations", [])
            expected_educations = expected_profile_data.get("educations", [])
            
            if len(result_educations) != len(expected_educations):
                compatibility_errors.append(f"Education count: {len(result_educations)} != {len(expected_educations)}")
            
            for i, (new_edu, expected_edu) in enumerate(zip(result_educations, expected_educations)):
                for field in ["institution", "degree", "from_date", "to_date", "description"]:
                    if new_edu.get(field) != expected_edu.get(field):
                        compatibility_errors.append(
                            f"Education {i} {field}: '{new_edu.get(field)}' != '{expected_edu.get(field)}'"
                        )
            
            # Interests validation
            result_interests = result.get("interests", [])
            expected_interests = expected_profile_data.get("interests", [])
            
            if len(result_interests) != len(expected_interests):
                compatibility_errors.append(f"Interest count: {len(result_interests)} != {len(expected_interests)}")
            
            # Accomplishments validation
            result_accomplishments = result.get("accomplishments", [])
            expected_accomplishments = expected_profile_data.get("accomplishments", [])
            
            if len(result_accomplishments) != len(expected_accomplishments):
                compatibility_errors.append(f"Accomplishment count: {len(result_accomplishments)} != {len(expected_accomplishments)}")
            
            # Contacts validation
            result_contacts = result.get("contacts", [])
            expected_contacts = expected_profile_data.get("contacts", [])
            
            if len(result_contacts) != len(expected_contacts):
                compatibility_errors.append(f"Contact count: {len(result_contacts)} != {len(expected_contacts)}")
            
            # If any errors, print them and fail
            if compatibility_errors:
                print("\n=== COMPATIBILITY ERRORS ===")
                for error in compatibility_errors:
                    print(f"❌ {error}")
                pytest.fail(f"Found {len(compatibility_errors)} compatibility issues")
            
            print("✅ Perfect compatibility with testdata/testscrape.txt")
    
    @pytest.mark.asyncio
    async def test_minimal_profile_format(self):
        """Test minimal profile returns expected format quickly"""
        with patch('linkedin_mcp_server.error_handler.safe_get_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_person = Mock()
            mock_person.model_dump.return_value = {
                "name": "Test User",
                "headline": "Software Developer",
                "location": "San Francisco, CA",
                "about": ["Passionate developer"],
                "company": "Tech Corp",
                "open_to_work": False,
            }
            mock_session_instance.get_profile.return_value = mock_person
            mock_session.return_value = mock_session_instance
            
            start_time = time.time()
            result = await get_person_profile_minimal("testuser")
            execution_time = time.time() - start_time
            
            # Performance requirement: should be very fast in unit test
            assert execution_time < 1.0, f"Minimal scraping took {execution_time:.2f}s in unit test"
            
            # Format validation
            assert result["name"] == "Test User"
            assert result["headline"] == "Software Developer"
            assert result["scraping_mode"] == "minimal"
            assert "job_title" in result
            assert result["job_title"] == "Software Developer"  # headline mapped to job_title
            
            print(f"✅ Minimal profile test passed in {execution_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_error_handling_compatibility(self):
        """Test that errors are properly handled and returned as MCP-compatible responses"""
        with patch('linkedin_mcp_server.error_handler.safe_get_session') as mock_session:
            mock_session.side_effect = Exception("Session creation failed")
            
            result = await get_person_profile("testuser")
            
            # Should return error dict, not raise exception
            assert isinstance(result, dict)
            assert "error" in result
            assert "message" in result
            assert result["error"] in ["unknown_error", "linkedin_scraper_error", "session_closed"]
            
            print("✅ Error handling compatibility confirmed")
    
    @pytest.mark.asyncio 
    async def test_tool_response_structure(self):
        """Test that all tool responses follow expected MCP structure"""
        with patch('linkedin_mcp_server.error_handler.safe_get_session') as mock_session:
            mock_session_instance = AsyncMock()
            mock_person = Mock()
            mock_person.model_dump.return_value = {
                "name": "Structure Test",
                "headline": "Test Engineer",
                "about": ["Testing structures"],
                "company": "Test Corp",
                "experiences": [],
                "educations": [],
                "interests": [],
                "honors": [],
                "languages": [],
                "connections": [],
                "open_to_work": False,
            }
            mock_session_instance.get_profile.return_value = mock_person
            mock_session.return_value = mock_session_instance
            
            # Test full profile structure
            full_result = await get_person_profile("testuser")
            
            # Required fields for full profile
            required_fields = [
                "name", "about", "experiences", "educations", "interests", 
                "accomplishments", "contacts", "company", "job_title", "open_to_work"
            ]
            
            for field in required_fields:
                assert field in full_result, f"Missing required field: {field}"
                
            # Test minimal profile structure  
            minimal_result = await get_person_profile_minimal("testuser")
            
            # Required fields for minimal profile
            minimal_required_fields = [
                "name", "headline", "location", "about", "company", "job_title", 
                "open_to_work", "scraping_mode"
            ]
            
            for field in minimal_required_fields:
                assert field in minimal_result, f"Missing required minimal field: {field}"
                
            assert minimal_result["scraping_mode"] == "minimal"
            
            print("✅ Tool response structure validation passed")


class TestSessionPersistence:
    """Test session persistence across multiple tool calls"""
    
    @pytest.mark.asyncio
    async def test_session_reuse_simulation(self):
        """Test that multiple calls would reuse the same session"""
        with patch('linkedin_mcp_server.session.manager.LinkedInSession') as mock_session_class:
            mock_session_instance = AsyncMock()
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session_instance.is_authenticated = AsyncMock(return_value=True)
            
            mock_person = Mock()
            mock_person.model_dump.return_value = {
                "name": "Session Test",
                "headline": "Test",
                "about": [],
                "company": "Test",
                "experiences": [],
                "educations": [],
                "interests": [],
                "honors": [],
                "languages": [],
                "connections": [],
                "open_to_work": False,
            }
            mock_session_instance.get_profile = AsyncMock(return_value=mock_person)
            
            mock_session_class.from_cookie.return_value = mock_session_instance
            
            with patch('linkedin_mcp_server.error_handler.safe_get_session') as mock_safe_session:
                mock_safe_session.return_value = mock_session_instance
                
                # Make multiple calls
                await get_person_profile_minimal("testuser1")
                await get_person_profile_minimal("testuser2") 
                await get_person_profile("testuser3")
                
                # Verify session was reused (safe_get_session should return same instance)
                assert mock_safe_session.call_count == 3
                
            print("✅ Session persistence simulation passed")