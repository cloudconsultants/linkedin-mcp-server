"""Configuration settings for the LinkedIn scraper."""

import os
from dataclasses import dataclass
from enum import Flag, auto
from typing import Optional

from patchright.async_api import ViewportSize
from fake_useragent import UserAgent


@dataclass
class StealthConfig:
    """Enhanced stealth configuration with headless and Docker support."""

    use_patchright: bool = True
    fallback_to_botright: bool = True
    enable_fingerprint_masking: bool = True
    session_warming: bool = True
    human_behavior_simulation: bool = True
    headless: bool = True  # REQUIRED: Must support headless mode
    max_concurrent_profiles: int = 3
    base_delay_range: tuple = (1.5, 4.0)
    reading_delay_range: tuple = (2.0, 6.0)
    rate_limit_per_minute: int = 1  # Maximum 1 profile per minute
    session_rotation_threshold: int = 5  # Rotate after 5 profiles
    stealth_wait_message: bool = True  # Inform user about delays

    @classmethod
    def from_stealth_profile(
        cls, profile_name: Optional[str] = None
    ) -> "StealthConfig":
        """Create StealthConfig from new stealth profile system.

        This method bridges between the new stealth profiles and legacy configuration,
        enabling backward compatibility during the migration period.

        Args:
            profile_name: Name of stealth profile (NO_STEALTH, MINIMAL_STEALTH, etc.)

        Returns:
            StealthConfig instance configured from the stealth profile
        """
        try:
            from linkedin_mcp_server.scraper.stealth.profiles import get_stealth_profile

            stealth_profile = get_stealth_profile(profile_name)
            return stealth_profile.to_legacy_config()
        except ImportError:
            # Fallback to default if stealth module not available
            return cls()


# Environment variable configuration for stealth system
def get_stealth_environment_config() -> dict:
    """Get stealth system configuration from environment variables.

    Returns:
        Dictionary with environment configuration for stealth system
    """
    return {
        "stealth_profile": os.getenv("STEALTH_PROFILE", "MINIMAL_STEALTH"),
        "use_new_stealth": os.getenv("USE_NEW_STEALTH", "false").lower() == "true",
        "stealth_telemetry": os.getenv("STEALTH_TELEMETRY", "true").lower() == "true",
        "stealth_config_path": os.getenv("STEALTH_CONFIG_PATH"),
    }


def is_new_stealth_enabled() -> bool:
    """Check if the new centralized stealth system should be used.

    Returns:
        True if new stealth system is enabled via environment variable
    """
    return os.getenv("USE_NEW_STEALTH", "false").lower() == "true"


class LinkedInDetectionError(Exception):
    """Raised when LinkedIn detection is suspected."""

    pass


class SessionKickedError(Exception):
    """Raised when LinkedIn invalidates session."""

    pass


class DynamicUserAgent:
    """Dynamic user agent management for stealth browsing."""

    def __init__(self):
        self.ua = UserAgent()

    def get_chrome_user_agent(self) -> str:
        """Get a realistic Chrome user agent."""
        return self.ua.chrome

    def get_random_user_agent(self) -> str:
        """Get a random realistic user agent."""
        return self.ua.random


class BrowserConfig:
    """Stealth-focused browser configuration settings."""

    VIEWPORT: ViewportSize = {"width": 1920, "height": 1080}
    TIMEOUT = 15000  # timeout in ms

    # Dynamic user agent - will be set by stealth manager
    _user_agent_manager = DynamicUserAgent()

    @classmethod
    def get_user_agent(cls) -> str:
        """Get dynamic user agent for stealth."""
        return cls._user_agent_manager.get_chrome_user_agent()

    # Stealth-focused Chrome args - removed automation detection triggers
    STEALTH_CHROME_ARGS = [
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-plugins-discovery",
        "--disable-translate",
        "--disable-default-apps",
        "--no-pings",
        "--disable-sync",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection",
    ]

    # Additional headless args for better stealth
    HEADLESS_STEALTH_ARGS = STEALTH_CHROME_ARGS + [
        "--headless=new",  # Use new headless mode
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--virtual-time-budget=5000",
    ]

    # Geolocation settings
    GEOLOCATION = {"latitude": 37.7749, "longitude": -122.4194}  # San Francisco

    # Performance settings
    MEMORY_PRESSURE_SETTINGS = {
        "memory_pressure_off": True,
        "max_old_space_size": 4096,
    }


class PersonScrapingFields(Flag):
    """Fields that can be scraped from LinkedIn person profiles.

    Each field corresponds to specific profile sections and navigation requirements:

    - BASIC_INFO: Name, headline, location, about (scraped from main page, ~2s)
    - EXPERIENCE: Work history (navigates to /details/experience, ~5s)
    - EDUCATION: Education history (navigates to /details/education, ~5s)
    - INTERESTS: Following/interests (navigates to /details/interests, ~5s)
    - ACCOMPLISHMENTS: Honors and languages (multiple navigations, ~6s)
    - CONTACTS: Contact info and connections (modal + navigation, ~8s)
    """

    BASIC_INFO = auto()  # Name, headline, location, about
    EXPERIENCE = auto()  # Work history and employment details
    EDUCATION = auto()  # Educational background and degrees
    INTERESTS = auto()  # Following companies/people and interests
    ACCOMPLISHMENTS = auto()  # Honors, awards, and languages
    CONTACTS = auto()  # Contact information and connections

    # Presets for common use cases
    MINIMAL = BASIC_INFO  # Fastest: basic info only (~2s)
    CAREER = BASIC_INFO | EXPERIENCE | EDUCATION  # Career-focused (~12s)
    ALL = (
        BASIC_INFO | EXPERIENCE | EDUCATION | INTERESTS | ACCOMPLISHMENTS | CONTACTS
    )  # Complete profile (~30s)


def get_active_stealth_config() -> StealthConfig:
    """Get the active stealth configuration.

    This function automatically selects between legacy and new stealth systems
    based on environment configuration.

    Returns:
        StealthConfig instance configured for current environment
    """
    env_config = get_stealth_environment_config()

    if env_config["use_new_stealth"]:
        # Use new stealth profile system
        return StealthConfig.from_stealth_profile(env_config["stealth_profile"])
    else:
        # Use legacy default configuration
        return StealthConfig()


def log_stealth_configuration() -> None:
    """Log current stealth configuration for debugging."""
    import logging

    logger = logging.getLogger(__name__)
    env_config = get_stealth_environment_config()

    logger.info("=== LinkedIn MCP Stealth Configuration ===")
    logger.info(f"Stealth Profile: {env_config['stealth_profile']}")
    logger.info(f"Use New Stealth: {env_config['use_new_stealth']}")
    logger.info(f"Telemetry Enabled: {env_config['stealth_telemetry']}")

    if env_config["use_new_stealth"]:
        logger.info("Using centralized stealth architecture (new system)")
    else:
        logger.info("Using legacy stealth system")

    logger.info("===========================================")
