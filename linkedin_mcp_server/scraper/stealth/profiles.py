"""Stealth profile configurations for different performance/detection trade-offs."""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from linkedin_mcp_server.scraper.config import StealthConfig


class NavigationMode(Enum):
    """Navigation strategies for accessing LinkedIn content."""

    DIRECT = "direct"  # Fast: Direct URL navigation (~5s)
    SEARCH_FIRST = "search"  # Slow: Search-first navigation (~45s, current default)


class SimulationLevel(Enum):
    """Human behavior simulation levels."""

    NONE = "none"  # No behavior simulation (fastest)
    BASIC = "basic"  # Minimal scrolling and interaction
    MODERATE = "moderate"  # Balanced interaction patterns
    COMPREHENSIVE = "comprehensive"  # Full behavior simulation (current default)


@dataclass
class DelayConfig:
    """Centralized delay configurations for stealth operations."""

    base: Tuple[float, float] = (1.5, 4.0)  # Random base delays
    reading: Tuple[float, float] = (2.0, 6.0)  # Content reading delays
    navigation: Tuple[float, float] = (1.0, 3.0)  # Navigation delays
    typing: Tuple[float, float] = (0.05, 0.15)  # Per-character typing delays
    scroll: Tuple[float, float] = (0.5, 1.5)  # Scroll action delays


@dataclass
class StealthProfile:
    """Configurable stealth behavior profiles for different use cases."""

    name: str
    navigation: NavigationMode
    delays: DelayConfig
    simulation: SimulationLevel
    lazy_loading: bool = True  # Always use intelligent loading
    telemetry: bool = True  # Performance monitoring
    enable_fingerprint_masking: bool = True
    session_warming: bool = True
    max_concurrent_profiles: int = 3
    rate_limit_per_minute: int = 1
    session_rotation_threshold: int = 5

    @classmethod
    def NO_STEALTH(cls) -> "StealthProfile":
        """Maximum speed profile with minimal stealth (50s target)."""
        return cls(
            name="NO_STEALTH",
            navigation=NavigationMode.DIRECT,
            delays=DelayConfig(
                base=(0.1, 0.3),
                reading=(0.2, 0.5),
                navigation=(0.1, 0.3),
                typing=(0.01, 0.03),
                scroll=(0.1, 0.3),
            ),
            simulation=SimulationLevel.NONE,
            lazy_loading=False,  # Disable for maximum speed
            telemetry=True,
            enable_fingerprint_masking=False,
            session_warming=False,
            max_concurrent_profiles=5,
            rate_limit_per_minute=10,
            session_rotation_threshold=20,
        )

    @classmethod
    def MINIMAL_STEALTH(cls) -> "StealthProfile":
        """Balanced profile for production use (75s target)."""
        return cls(
            name="MINIMAL_STEALTH",
            navigation=NavigationMode.DIRECT,
            delays=DelayConfig(
                base=(0.5, 1.0),
                reading=(0.5, 1.5),
                navigation=(0.3, 0.8),
                typing=(0.03, 0.08),
                scroll=(0.3, 0.6),
            ),
            simulation=SimulationLevel.BASIC,
            lazy_loading=True,
            telemetry=True,
            enable_fingerprint_masking=True,
            session_warming=False,
            max_concurrent_profiles=3,
            rate_limit_per_minute=3,
            session_rotation_threshold=10,
        )

    @classmethod
    def MODERATE_STEALTH(cls) -> "StealthProfile":
        """Moderate stealth with good performance (150s target)."""
        return cls(
            name="MODERATE_STEALTH",
            navigation=NavigationMode.DIRECT,
            delays=DelayConfig(
                base=(1.0, 2.5),
                reading=(1.5, 3.0),
                navigation=(0.8, 2.0),
                typing=(0.05, 0.12),
                scroll=(0.5, 1.0),
            ),
            simulation=SimulationLevel.MODERATE,
            lazy_loading=True,
            telemetry=True,
            enable_fingerprint_masking=True,
            session_warming=True,
            max_concurrent_profiles=3,
            rate_limit_per_minute=2,
            session_rotation_threshold=7,
        )

    @classmethod
    def MAXIMUM_STEALTH(cls) -> "StealthProfile":
        """Maximum stealth profile matching current system (295s)."""
        return cls(
            name="MAXIMUM_STEALTH",
            navigation=NavigationMode.SEARCH_FIRST,
            delays=DelayConfig(
                base=(1.5, 4.0),
                reading=(2.0, 6.0),
                navigation=(1.0, 3.0),
                typing=(0.05, 0.15),
                scroll=(0.5, 1.5),
            ),
            simulation=SimulationLevel.COMPREHENSIVE,
            lazy_loading=True,
            telemetry=True,
            enable_fingerprint_masking=True,
            session_warming=True,
            max_concurrent_profiles=3,
            rate_limit_per_minute=1,
            session_rotation_threshold=5,
        )

    def to_legacy_config(self) -> StealthConfig:
        """Convert to legacy StealthConfig for backward compatibility."""
        return StealthConfig(
            use_patchright=True,
            fallback_to_botright=True,
            enable_fingerprint_masking=self.enable_fingerprint_masking,
            session_warming=self.session_warming,
            human_behavior_simulation=self.simulation != SimulationLevel.NONE,
            headless=True,
            max_concurrent_profiles=self.max_concurrent_profiles,
            base_delay_range=self.delays.base,
            reading_delay_range=self.delays.reading,
            rate_limit_per_minute=self.rate_limit_per_minute,
            session_rotation_threshold=self.session_rotation_threshold,
            stealth_wait_message=True,
        )


def get_stealth_profile(
    profile_name: Optional[str] = None, config_path: Optional[str] = None
) -> StealthProfile:
    """Get a stealth profile by name or from configuration.

    Args:
        profile_name: Name of the profile (NO_STEALTH, MINIMAL_STEALTH, etc.)
        config_path: Path to custom configuration file (future enhancement)

    Returns:
        StealthProfile instance configured for the requested profile
    """
    if profile_name is None:
        profile_name = os.getenv("STEALTH_PROFILE", "MINIMAL_STEALTH")

    # Map profile names to factory methods
    profile_map = {
        "NO_STEALTH": StealthProfile.NO_STEALTH,
        "MINIMAL_STEALTH": StealthProfile.MINIMAL_STEALTH,
        "MODERATE_STEALTH": StealthProfile.MODERATE_STEALTH,
        "MAXIMUM_STEALTH": StealthProfile.MAXIMUM_STEALTH,
    }

    profile_name = profile_name.upper()
    if profile_name not in profile_map:
        raise ValueError(
            f"Unknown stealth profile: {profile_name}. "
            f"Available profiles: {', '.join(profile_map.keys())}"
        )

    return profile_map[profile_name]()
