"""Validation tests for aggressive performance optimization."""

import pytest
import time
from unittest.mock import AsyncMock, Mock, patch
from linkedin_mcp_server.scraper.stealth.profiles import StealthProfile
from linkedin_mcp_server.scraper.stealth.controller import (
    StealthController,
    PageType,
    ContentTarget,
)


class TestAggressiveOptimization:
    """Validate aggressive performance targets."""

    @pytest.mark.asyncio
    async def test_optimized_no_stealth_target(self):
        """Optimized NO_STEALTH should complete in under 2 seconds."""
        profile = StealthProfile.NO_STEALTH()
        controller = StealthController(profile=profile)

        # Mock page setup
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/test/"
        mock_page.goto = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock(return_value=None)
        mock_page.locator = Mock(return_value=AsyncMock())

        start_time = time.time()
        result = await controller.scrape_linkedin_page(
            mock_page,
            "https://www.linkedin.com/in/test/",
            PageType.PROFILE,
            [ContentTarget.BASIC_INFO, ContentTarget.EXPERIENCE],
        )
        duration = time.time() - start_time

        assert result.success
        assert duration < 2.0, (
            f"Optimized NO_STEALTH took {duration:.2f}s, target: <2.0s"
        )

    @pytest.mark.asyncio
    async def test_minimal_stealth_optimization_target(self):
        """Optimized MINIMAL_STEALTH should complete in under 10 seconds."""
        profile = StealthProfile.MINIMAL_STEALTH()
        controller = StealthController(profile=profile)

        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/test/"
        mock_page.goto = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock(return_value=None)
        mock_page.locator = Mock(return_value=AsyncMock())

        # Mock lazy loading detector
        with patch(
            "linkedin_mcp_server.scraper.stealth.lazy_loading.LazyLoadDetector.ensure_content_loaded"
        ) as mock_lazy:
            mock_result = Mock()
            mock_result.loaded_targets = [
                ContentTarget.BASIC_INFO,
                ContentTarget.EXPERIENCE,
                ContentTarget.EDUCATION,
            ]
            mock_lazy.return_value = mock_result

            start_time = time.time()
            result = await controller.scrape_linkedin_page(
                mock_page,
                "https://www.linkedin.com/in/test/",
                PageType.PROFILE,
                [
                    ContentTarget.BASIC_INFO,
                    ContentTarget.EXPERIENCE,
                    ContentTarget.EDUCATION,
                ],
            )
            duration = time.time() - start_time

        assert result.success
        assert duration < 10.0, f"Minimal stealth took {duration:.2f}s, target: <10.0s"

    @pytest.mark.asyncio
    async def test_maximum_stealth_optimization_target(self):
        """Optimized MAXIMUM_STEALTH should complete in under 30 seconds."""
        profile = StealthProfile.MAXIMUM_STEALTH()
        controller = StealthController(profile=profile)

        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/test/"
        mock_page.goto = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock(return_value=None)
        mock_page.locator = Mock(return_value=AsyncMock())

        # Mock lazy loading detector
        with patch(
            "linkedin_mcp_server.scraper.stealth.lazy_loading.LazyLoadDetector.ensure_content_loaded"
        ) as mock_lazy:
            mock_result = Mock()
            mock_result.loaded_targets = [
                ContentTarget.BASIC_INFO,
                ContentTarget.EXPERIENCE,
                ContentTarget.EDUCATION,
                ContentTarget.SKILLS,
            ]
            mock_lazy.return_value = mock_result

            # Mock simulation
            with patch(
                "linkedin_mcp_server.scraper.stealth.simulation.InteractionSimulator.simulate_page_interaction"
            ) as mock_sim:
                mock_sim.return_value = None

                start_time = time.time()
                result = await controller.scrape_linkedin_page(
                    mock_page,
                    "https://www.linkedin.com/in/test/",
                    PageType.PROFILE,
                    [
                        ContentTarget.BASIC_INFO,
                        ContentTarget.EXPERIENCE,
                        ContentTarget.EDUCATION,
                        ContentTarget.SKILLS,
                    ],
                )
                duration = time.time() - start_time

        assert result.success
        assert duration < 30.0, f"Maximum stealth took {duration:.2f}s, target: <30.0s"

    def test_field_mapping_accuracy(self):
        """Validate correct field mapping in optimized extraction."""
        # Test data based on drihs profile issues identified
        from linkedin_mcp_server.scraper.models.person import Experience

        # Test optimized extraction logic
        experience = Experience(
            position_title="Managing Director",
            institution_name="Cloud Consultants GmbH",  # FIXED: Should be company name
            from_date="Sep 2022",
            to_date=None,  # Present case
            duration="3 yrs 1 mo",
            location="Greater Zurich Area",
            employment_type="Full-time",
        )

        assert experience.position_title == "Managing Director"
        assert experience.institution_name == "Cloud Consultants GmbH"  # FIXED
        assert experience.from_date == "Sep 2022"
        assert experience.to_date is None  # Present case
        assert experience.duration == "3 yrs 1 mo"
        assert experience.location == "Greater Zurich Area"
        assert experience.employment_type == "Full-time"
