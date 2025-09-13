# linkedin_mcp_server/setup.py
"""
Interactive setup flows for LinkedIn MCP Server authentication configuration.

Handles credential collection, cookie extraction, validation, and secure storage
with multiple authentication methods including cookie input and credential-based login.
Provides temporary driver management and comprehensive retry logic.
"""

import logging
from contextlib import contextmanager
from typing import Dict, Iterator

import inquirer

from linkedin_mcp_server.authentication import store_authentication
from linkedin_mcp_server.config import get_config
from linkedin_mcp_server.config.messages import ErrorMessages, InfoMessages
from linkedin_mcp_server.config.providers import (
    get_credentials_from_keyring,
    save_credentials_to_keyring,
)
from linkedin_mcp_server.config.schema import AppConfig
from linkedin_mcp_server.exceptions import CredentialsNotFoundError

logger = logging.getLogger(__name__)


def get_credentials_for_setup() -> Dict[str, str]:
    """
    Get LinkedIn credentials for setup purposes.

    Returns:
        Dict[str, str]: Dictionary with email and password

    Raises:
        CredentialsNotFoundError: If credentials cannot be obtained
    """
    config = get_config()

    # First, try configuration (includes environment variables)
    if config.linkedin.email and config.linkedin.password:
        logger.info("Using LinkedIn credentials from configuration")
        return {"email": config.linkedin.email, "password": config.linkedin.password}

    # Second, try keyring
    credentials = get_credentials_from_keyring()
    if credentials["email"] and credentials["password"]:
        logger.info("Using LinkedIn credentials from keyring")
        return {"email": credentials["email"], "password": credentials["password"]}

    # If in non-interactive mode and no credentials found, raise error
    if not config.is_interactive:
        raise CredentialsNotFoundError(ErrorMessages.no_credentials_found())

    # Otherwise, prompt for credentials
    return prompt_for_credentials()


def prompt_for_credentials() -> Dict[str, str]:
    """
    Prompt user for LinkedIn credentials.

    Returns:
        Dict[str, str]: Dictionary with email and password

    Raises:
        KeyboardInterrupt: If user cancels input
    """
    print("🔑 LinkedIn credentials required for setup")
    questions = [
        inquirer.Text("email", message="LinkedIn Email"),
        inquirer.Password("password", message="LinkedIn Password"),
    ]
    credentials: Dict[str, str] = inquirer.prompt(questions)

    if not credentials:
        raise KeyboardInterrupt("Credential input was cancelled")

    # Store credentials securely in keyring
    if save_credentials_to_keyring(credentials["email"], credentials["password"]):
        logger.info(InfoMessages.credentials_stored_securely())
    else:
        logger.warning(InfoMessages.keyring_storage_failed())

    return credentials


@contextmanager
def temporary_playwright_session() -> Iterator:
    """
    Context manager for creating temporary Playwright session with automatic cleanup.

    Yields:
        LinkedInSession: Configured Playwright session instance

    Raises:
        Exception: If session creation fails
    """
    from linkedin_mcp_server.scraper.session import LinkedInSession

    session = None
    try:
        # Create temporary session with placeholder auth
        from linkedin_mcp_server.scraper.auth import CookieAuth

        auth = CookieAuth("placeholder")
        session = LinkedInSession(auth)
        yield session
    finally:
        if session:
            try:
                import asyncio

                asyncio.run(session.close())
            except Exception:
                pass  # Best effort cleanup


async def capture_cookie_from_credentials(email: str, password: str) -> str:
    """
    Login with credentials and capture session cookie using Playwright.

    Args:
        email: LinkedIn email
        password: LinkedIn password

    Returns:
        str: Captured session cookie

    Raises:
        Exception: If login or cookie capture fails
    """
    from linkedin_mcp_server.scraper.session import LinkedInSession

    config: AppConfig = get_config()
    interactive: bool = config.is_interactive
    logger.info(f"Logging in to LinkedIn... Interactive: {interactive}")

    # Create session with password authentication
    from linkedin_mcp_server.scraper.auth import PasswordAuth

    auth = PasswordAuth(email, password, interactive=interactive)
    _session = LinkedInSession(
        auth, headless=config.chrome.headless
    )  # Will be used in future implementation

    try:
        # TODO: Login and cookie extraction needs to be implemented
        # This is a placeholder for now
        raise NotImplementedError(
            "Cookie extraction not yet implemented with Playwright"
        )

        # Future implementation would be:
        # await session.login()
        # cookie = await session.get_session_cookie()
        # if cookie:
        #     logger.info("Successfully captured session cookie")
        #     return cookie
        # else:
        #     raise Exception("Failed to capture session cookie from browser")
    finally:
        # await session.close()  # TODO: Implement session cleanup
        pass


async def test_cookie_validity(cookie: str) -> bool:
    """
    Test if a cookie is valid by attempting to use it with Playwright session.

    Args:
        cookie: LinkedIn session cookie to test

    Returns:
        bool: True if cookie is valid, False otherwise
    """
    try:
        from linkedin_mcp_server.session.manager import PlaywrightSessionManager

        # Try to create and authenticate a session
        session = await PlaywrightSessionManager.get_or_create_session(cookie)
        is_authenticated = await session.is_authenticated()

        return is_authenticated
    except Exception as e:
        logger.warning(f"Cookie validation failed: {e}")
        return False


def prompt_for_cookie() -> str:
    """
    Prompt user to input LinkedIn cookie directly.

    Returns:
        str: LinkedIn session cookie

    Raises:
        KeyboardInterrupt: If user cancels input
        ValueError: If cookie format is invalid
    """
    print("🍪 Please provide your LinkedIn session cookie")
    cookie = inquirer.text("LinkedIn Cookie")

    if not cookie:
        raise KeyboardInterrupt("Cookie input was cancelled")

    # Normalize cookie format
    if cookie.startswith("li_at="):
        cookie: str = cookie.split("li_at=")[1]

    return cookie


async def run_interactive_setup() -> str:
    """
    Run interactive setup to configure authentication.

    Returns:
        str: Configured LinkedIn session cookie

    Raises:
        Exception: If setup fails
    """
    print("🔗 LinkedIn MCP Server Setup")
    print("Choose how you'd like to authenticate:")

    # Ask user for setup method
    setup_method = inquirer.list_input(
        "Setup method",
        choices=[
            ("I have a LinkedIn cookie", "cookie"),
            ("Login with email/password to get cookie", "credentials"),
        ],
        default="cookie",
    )

    if setup_method == "cookie":
        # User provides cookie directly
        cookie = prompt_for_cookie()

        # Test the cookie with Playwright session
        print("🔍 Testing provided cookie...")
        if await test_cookie_validity(cookie):
            # Store the valid cookie
            store_authentication(cookie)
            logger.info("✅ Authentication configured successfully")
            return cookie
        else:
            print("❌ The provided cookie is invalid or expired")
            retry = inquirer.confirm(
                "Would you like to try with email/password instead?", default=True
            )
            if not retry:
                raise Exception("Setup cancelled - invalid cookie provided")

            # Fall through to credentials flow
            setup_method = "credentials"

    if setup_method == "credentials":
        # Get credentials and attempt login with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                credentials = get_credentials_for_setup()

                print("🔑 Logging in to capture session cookie...")
                cookie = await capture_cookie_from_credentials(
                    credentials["email"], credentials["password"]
                )

                # Store the captured cookie
                store_authentication(cookie)
                logger.info("✅ Authentication configured successfully")
                return cookie

            except Exception as e:
                logger.error(f"Login failed: {e}")
                print(f"❌ Login failed: {e}")

                if attempt < max_retries - 1:
                    retry = inquirer.confirm(
                        "Would you like to try with different credentials?",
                        default=True,
                    )
                    if not retry:
                        break
                    # Clear stored credentials to prompt for new ones
                    from linkedin_mcp_server.config.providers import (
                        clear_credentials_from_keyring,
                    )

                    clear_credentials_from_keyring()
                else:
                    raise Exception(f"Setup failed after {max_retries} attempts")

        raise Exception("Setup cancelled by user")

    # This should never be reached, but ensures type checker knows all paths are covered
    raise Exception("Unexpected setup flow completion")


async def run_cookie_extraction_setup() -> str:
    """
    Run setup specifically for cookie extraction (--get-cookie mode).

    Returns:
        str: Captured LinkedIn session cookie for display

    Raises:
        Exception: If setup fails
    """
    logger.info("🔗 LinkedIn MCP Server - Cookie Extraction mode started")
    print("🔗 LinkedIn MCP Server - Cookie Extraction")

    # Get credentials
    credentials: Dict[str, str] = get_credentials_for_setup()

    # Capture cookie
    cookie: str = await capture_cookie_from_credentials(
        credentials["email"], credentials["password"]
    )

    return cookie
