import logging
from patchright.async_api import BrowserContext, Page

from ..exceptions import InvalidCredentialsError
from .base import LinkedInAuth

logger = logging.getLogger(__name__)


class CookieAuth(LinkedInAuth):
    """Cookie-based LinkedIn authentication using li_at cookie."""

    def __init__(self, cookie: str):
        """Initialize cookie authentication.

        Args:
            cookie: LinkedIn li_at cookie value

        Raises:
            ValueError: If cookie is empty
            InvalidCredentialsError: If cookie format is invalid
        """
        self.cookie = cookie.strip()
        if not self.cookie:
            raise ValueError("Cookie cannot be empty")

        # Validate cookie format upfront
        if not self.is_cookie_valid():
            raise InvalidCredentialsError("Invalid LinkedIn cookie format")

    async def _customize_context(self, context: BrowserContext):
        """Add LinkedIn cookie to the existing context.

        Args:
            context: Browser context instance
        """
        # Set the li_at cookie BEFORE creating any pages
        await context.add_cookies(
            [
                {
                    "name": "li_at",
                    "value": self.cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None",
                }
            ]
        )

    async def _authenticate(self, page: Page) -> bool:
        """Authenticate using li_at cookie.

        Args:
            page: Playwright page instance

        Returns:
            True if authentication successful

        Raises:
            InvalidCredentialsError: Invalid or expired cookie
            LoginTimeoutError: Authentication process timed out
        """
        try:
            # Import here to avoid circular imports
            from linkedin_mcp_server.scraper.browser.behavioral import (
                warm_linkedin_session,
            )
            from linkedin_mcp_server.scraper.config import StealthConfig

            # Warm the session AFTER cookies are set
            logger.info("Warming LinkedIn session with authentication...")
            stealth_config = StealthConfig()
            await warm_linkedin_session(page, stealth_config)

            # Legacy approach: Trust that cookie is valid since minimal warming succeeded
            # The actual authentication will be validated when accessing profiles directly
            logger.info(
                "Cookie authentication completed - ready for direct profile access"
            )
            return True

        except Exception as e:
            raise InvalidCredentialsError(
                f"Invalid or expired li_at cookie: {str(e)}"
            ) from e

    def is_cookie_valid(self) -> bool:
        """Basic validation of cookie format.

        Returns:
            True if cookie appears to have valid format
        """
        import re

        if len(self.cookie) < 100:  # LinkedIn cookies are quite long
            return False

        # Check if cookie contains only valid characters
        valid_pattern = re.compile(r"^[A-Za-z0-9\-_]+$")
        return valid_pattern.match(self.cookie) is not None
