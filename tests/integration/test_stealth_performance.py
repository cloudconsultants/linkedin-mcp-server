"""Integration tests for stealth system performance."""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from linkedin_mcp_server.scraper.stealth.controller import (
    StealthController,
    PageType,
    ContentTarget
)
from linkedin_mcp_server.scraper.stealth.profiles import StealthProfile


class TestStealthPerformance:
    """Test performance characteristics of the stealth system."""
    
    @pytest.mark.asyncio
    async def test_no_stealth_performance_target(self):
        """NO_STEALTH profile should achieve <10s for basic operations."""
        profile = StealthProfile.NO_STEALTH()
        controller = StealthController(profile=profile, telemetry=False)
        
        # Mock page operations to simulate fast responses
        mock_page = AsyncMock()
        
        start_time = time.time()
        
        # Simulate basic profile scraping
        result = await controller.scrape_linkedin_page(
            page=mock_page,
            url="https://linkedin.com/in/testuser",
            page_type=PageType.PROFILE,
            content_targets=[ContentTarget.BASIC_INFO]
        )
        
        duration = time.time() - start_time
        
        # Should complete quickly with NO_STEALTH profile
        assert duration < 10.0  # Target: <10s for basic operations
        assert result.success
        assert result.profile_used == "NO_STEALTH"
    
    @pytest.mark.asyncio
    async def test_minimal_stealth_performance_target(self):
        """MINIMAL_STEALTH profile should achieve reasonable performance."""
        profile = StealthProfile.MINIMAL_STEALTH()
        controller = StealthController(profile=profile, telemetry=False)
        
        mock_page = AsyncMock()
        
        start_time = time.time()
        
        # Simulate comprehensive profile scraping
        result = await controller.scrape_linkedin_page(
            page=mock_page,
            url="https://linkedin.com/in/testuser",
            page_type=PageType.PROFILE,
            content_targets=[
                ContentTarget.BASIC_INFO,
                ContentTarget.EXPERIENCE,
                ContentTarget.EDUCATION
            ]
        )
        
        duration = time.time() - start_time
        
        # Should be faster than legacy but not as fast as NO_STEALTH
        assert duration < 30.0  # Much faster than legacy 300s target
        assert result.success
        assert result.profile_used == "MINIMAL_STEALTH"
    
    @pytest.mark.asyncio
    async def test_performance_regression_prevention(self):
        """New system should not be slower than reasonable thresholds."""
        profiles_to_test = [
            (StealthProfile.NO_STEALTH(), 15.0),  # <15s for fastest
            (StealthProfile.MINIMAL_STEALTH(), 45.0),  # <45s for balanced
            (StealthProfile.MODERATE_STEALTH(), 90.0),  # <90s for moderate
        ]
        
        for profile, max_duration in profiles_to_test:
            controller = StealthController(profile=profile, telemetry=False)
            mock_page = AsyncMock()
            
            start_time = time.time()
            
            result = await controller.scrape_linkedin_page(
                page=mock_page,
                url="https://linkedin.com/in/testuser",
                page_type=PageType.PROFILE,
                content_targets=[ContentTarget.BASIC_INFO, ContentTarget.EXPERIENCE]
            )
            
            duration = time.time() - start_time
            
            assert duration < max_duration, (
                f"{profile.name} took {duration:.1f}s, "
                f"expected <{max_duration}s"
            )
            assert result.success
    
    @pytest.mark.asyncio
    async def test_content_loading_intelligence(self):
        """Intelligent content loading should be faster than fixed waits."""
        from linkedin_mcp_server.scraper.stealth.lazy_loading import LazyLoadDetector
        from linkedin_mcp_server.scraper.stealth.profiles import StealthProfile
        
        detector = LazyLoadDetector()
        profile = StealthProfile.MINIMAL_STEALTH()
        
        # Mock page with content already loaded
        mock_page = AsyncMock()
        mock_page.locator.return_value.count = AsyncMock(return_value=1)
        mock_page.locator.return_value.first.is_visible = AsyncMock(return_value=True)
        
        start_time = time.time()
        
        result = await detector.ensure_content_loaded(
            page=mock_page,
            targets=[ContentTarget.BASIC_INFO],
            profile=profile,
            max_wait_time=5
        )
        
        duration = time.time() - start_time
        
        # Should detect immediately without waiting
        assert duration < 1.0  # Should be nearly instant
        assert result.success
        assert ContentTarget.BASIC_INFO in result.loaded_targets
    
    @pytest.mark.asyncio 
    async def test_telemetry_performance_tracking(self):
        """Performance telemetry should accurately track metrics."""
        from linkedin_mcp_server.scraper.stealth.telemetry import PerformanceTelemetry
        
        telemetry = PerformanceTelemetry(persist_metrics=False)
        
        # Record some test metrics
        await telemetry.record_success(
            url="https://linkedin.com/in/test1",
            duration=25.5,
            profile_name="MINIMAL_STEALTH",
            page_type="profile"
        )
        
        await telemetry.record_success(
            url="https://linkedin.com/in/test2", 
            duration=8.2,
            profile_name="NO_STEALTH",
            page_type="profile"
        )
        
        # Get statistics
        minimal_stats = telemetry.get_profile_stats("MINIMAL_STEALTH")
        no_stealth_stats = telemetry.get_profile_stats("NO_STEALTH")
        
        assert minimal_stats is not None
        assert minimal_stats.avg_duration == 25.5
        assert minimal_stats.success_rate == 1.0
        
        assert no_stealth_stats is not None
        assert no_stealth_stats.avg_duration == 8.2
        assert no_stealth_stats.success_rate == 1.0
        
        # Get performance comparison
        comparisons = telemetry.get_performance_comparison()
        assert len(comparisons) == 2
        
        # NO_STEALTH should show significant improvement
        if "NO_STEALTH" in comparisons:
            assert comparisons["NO_STEALTH"]["improvement_pct"] > 60  # >60% faster
    
    def test_stealth_profile_switching(self):
        """Environment variable profile switching should work correctly."""
        with patch.dict('os.environ', {"STEALTH_PROFILE": "NO_STEALTH"}):
            controller = StealthController.from_config()
            assert controller.profile.name == "NO_STEALTH"
            assert controller.profile.simulation.value == "none"
        
        with patch.dict('os.environ', {"STEALTH_PROFILE": "MAXIMUM_STEALTH"}):
            controller = StealthController.from_config()
            assert controller.profile.name == "MAXIMUM_STEALTH"
            assert controller.profile.simulation.value == "comprehensive"