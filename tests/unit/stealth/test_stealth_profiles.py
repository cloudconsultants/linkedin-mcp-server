"""Unit tests for stealth profiles and configuration."""

import pytest
import os
from unittest.mock import patch

from linkedin_mcp_server.scraper.stealth.profiles import (
    StealthProfile,
    NavigationMode,
    SimulationLevel,
    get_stealth_profile,
)


class TestStealthProfiles:
    """Test stealth profile configurations."""

    def test_no_stealth_profile_settings(self):
        """NO_STEALTH profile should have minimal settings for maximum speed."""
        profile = StealthProfile.NO_STEALTH()

        assert profile.name == "NO_STEALTH"
        assert profile.navigation == NavigationMode.DIRECT
        assert profile.simulation == SimulationLevel.NONE
        assert profile.enable_fingerprint_masking is False
        assert profile.session_warming is False
        assert profile.rate_limit_per_minute == 10  # Higher throughput

        # Delays should be minimal
        assert profile.delays.base[0] < 0.5
        assert profile.delays.reading[0] < 1.0

    def test_minimal_stealth_profile_settings(self):
        """MINIMAL_STEALTH should balance speed and stealth."""
        profile = StealthProfile.MINIMAL_STEALTH()

        assert profile.name == "MINIMAL_STEALTH"
        assert profile.navigation == NavigationMode.DIRECT
        assert profile.simulation == SimulationLevel.BASIC
        assert profile.enable_fingerprint_masking is True
        assert profile.session_warming is False
        assert profile.rate_limit_per_minute == 3

        # Delays should be moderate
        assert 0.5 <= profile.delays.base[0] <= 1.0
        assert 0.5 <= profile.delays.reading[0] <= 2.0

    def test_maximum_stealth_profile_settings(self):
        """MAXIMUM_STEALTH should match current system behavior."""
        profile = StealthProfile.MAXIMUM_STEALTH()

        assert profile.name == "MAXIMUM_STEALTH"
        assert profile.navigation == NavigationMode.SEARCH_FIRST
        assert profile.simulation == SimulationLevel.COMPREHENSIVE
        assert profile.enable_fingerprint_masking is True
        assert profile.session_warming is True
        assert profile.rate_limit_per_minute == 1

        # Delays should match current system
        assert profile.delays.base == (1.5, 4.0)
        assert profile.delays.reading == (2.0, 6.0)

    def test_profile_environment_variable_loading(self):
        """Profile should load from STEALTH_PROFILE environment variable."""
        with patch.dict(os.environ, {"STEALTH_PROFILE": "NO_STEALTH"}):
            profile = get_stealth_profile()
            assert profile.name == "NO_STEALTH"

        with patch.dict(os.environ, {"STEALTH_PROFILE": "MAXIMUM_STEALTH"}):
            profile = get_stealth_profile()
            assert profile.name == "MAXIMUM_STEALTH"

    def test_invalid_profile_name_raises_error(self):
        """Invalid profile name should raise ValueError."""
        with pytest.raises(ValueError):
            get_stealth_profile("INVALID_PROFILE")

    def test_legacy_config_conversion(self):
        """Stealth profiles should convert to legacy StealthConfig correctly."""
        no_stealth = StealthProfile.NO_STEALTH()
        legacy_config = no_stealth.to_legacy_config()

        assert legacy_config.enable_fingerprint_masking is False
        assert legacy_config.session_warming is False
        assert legacy_config.human_behavior_simulation is False
        assert legacy_config.rate_limit_per_minute == 10

        max_stealth = StealthProfile.MAXIMUM_STEALTH()
        legacy_config = max_stealth.to_legacy_config()

        assert legacy_config.enable_fingerprint_masking is True
        assert legacy_config.session_warming is True
        assert legacy_config.human_behavior_simulation is True
        assert legacy_config.rate_limit_per_minute == 1
