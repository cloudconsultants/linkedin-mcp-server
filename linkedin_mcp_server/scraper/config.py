"""Configuration settings for the LinkedIn scraper."""

from dataclasses import dataclass
from enum import Flag, auto
from playwright.async_api import ViewportSize
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
        "--disable-background-networking",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection",
    ]

    # Additional stealth args for headless mode specifically
    HEADLESS_STEALTH_ARGS = STEALTH_CHROME_ARGS + [
        "--disable-features=VizDisplayCompositor",
        "--run-all-compositor-stages-before-draw",
        "--disable-threaded-animation",
        "--disable-checker-imaging",
        "--disable-new-content-rendering-timeout",
        "--disable-threaded-scrolling",
        "--disable-image-animation-resync",
    ]

    # Legacy problematic args - kept for reference but NOT used
    LEGACY_PROBLEMATIC_ARGS = [
        "--disable-web-security",  # 🚨 RED FLAG - suspicious
        "--disable-gpu",  # 🚨 RED FLAG - headless indicator
        "--disable-background-timer-throttling",  # 🚨 RED FLAG - automation pattern
        "--disable-backgrounding-occluded-windows",  # 🚨 RED FLAG - automation pattern
        "--disable-renderer-backgrounding",  # 🚨 RED FLAG - automation pattern
    ]


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
