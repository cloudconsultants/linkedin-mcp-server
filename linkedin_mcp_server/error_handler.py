# src/linkedin_mcp_server/error_handler.py
"""
Centralized error handling for LinkedIn MCP Server with structured responses.

Provides DRY approach to error handling across all tools with consistent MCP response
format, specific LinkedIn error categorization, and proper logging integration.
Eliminates code duplication while ensuring user-friendly error messages.
"""

import logging
from typing import Any, Dict, List

# Import fast-linkedin-scraper exceptions
from linkedin_mcp_server.scraper.exceptions import (
    InvalidCredentialsError as FastInvalidCredentialsError,
    RateLimitError as FastRateLimitError,
    SecurityChallengeError as FastSecurityChallengeError,
    LoginTimeoutError as FastLoginTimeoutError,
    CredentialsNotFoundError as FastCredentialsNotFoundError,
    DriverInitializationError,
    LinkedInScraperError,
)

from linkedin_mcp_server.exceptions import (
    CredentialsNotFoundError,
    LinkedInMCPError,
)

# Import Playwright exceptions for additional error handling
try:
    from playwright._impl._errors import (
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
    )
except ImportError:
    # Fallback if playwright not installed yet
    PlaywrightError: type[Exception] = Exception
    PlaywrightTimeoutError: type[Exception] = Exception


def handle_tool_error(exception: Exception, context: str = "") -> Dict[str, Any]:
    """
    Handle errors from tool functions and return structured responses.

    Args:
        exception: The exception that occurred
        context: Context about which tool failed

    Returns:
        Structured error response dictionary
    """
    return convert_exception_to_response(exception, context)


def handle_tool_error_list(
    exception: Exception, context: str = ""
) -> List[Dict[str, Any]]:
    """
    Handle errors from tool functions that return lists.

    Args:
        exception: The exception that occurred
        context: Context about which tool failed

    Returns:
        List containing structured error response dictionary
    """
    return convert_exception_to_list_response(exception, context)


def convert_exception_to_response(
    exception: Exception, context: str = ""
) -> Dict[str, Any]:
    """
    Convert an exception to a structured MCP response with Playwright support.

    Args:
        exception: The exception to convert
        context: Additional context about where the error occurred

    Returns:
        Structured error response dictionary
    """
    # Handle credentials not found (both old and new)
    if isinstance(exception, (CredentialsNotFoundError, FastCredentialsNotFoundError)):
        return {
            "error": "authentication_not_found",
            "message": str(exception),
            "resolution": "Provide LinkedIn cookie via LINKEDIN_COOKIE environment variable or run setup",
        }

    # Handle invalid credentials (fast-linkedin-scraper)
    elif isinstance(exception, FastInvalidCredentialsError):
        return {
            "error": "invalid_credentials",
            "message": str(exception),
            "resolution": "Check your LinkedIn cookie - it may be expired or invalid",
        }

    # Handle security challenges (fast-linkedin-scraper)
    elif isinstance(exception, FastSecurityChallengeError):
        return {
            "error": "security_challenge_required",
            "message": str(exception),
            "challenge_url": getattr(exception, "challenge_url", None),
            "resolution": "Complete the security challenge manually and try again",
        }

    # Handle rate limiting (fast-linkedin-scraper)
    elif isinstance(exception, FastRateLimitError):
        return {
            "error": "rate_limit",
            "message": str(exception),
            "resolution": "Wait before attempting to scrape again - LinkedIn has temporarily blocked requests",
        }

    # Handle login timeouts (fast-linkedin-scraper)
    elif isinstance(exception, FastLoginTimeoutError):
        return {
            "error": "login_timeout",
            "message": str(exception),
            "resolution": "Check network connection and try again - LinkedIn login process timed out",
        }

    # Handle driver initialization errors
    elif isinstance(exception, DriverInitializationError):
        return {
            "error": "browser_initialization_failed",
            "message": str(exception),
            "resolution": "Ensure Playwright browsers are installed: python -m playwright install",
        }

    # Handle Playwright-specific errors
    elif isinstance(exception, PlaywrightTimeoutError):
        return {
            "error": "playwright_timeout",
            "message": f"Page load or interaction timed out: {str(exception)}",
            "resolution": "LinkedIn may be slow or blocking requests. Wait and retry.",
        }

    elif isinstance(exception, PlaywrightError):
        error_msg = str(exception)

        # Handle specific Playwright error patterns
        if "net::ERR_NETWORK_CHANGED" in error_msg:
            return {
                "error": "network_error",
                "message": "Network connection interrupted during scraping",
                "resolution": "Check network connectivity and try again",
            }
        elif "Target page, context or browser has been closed" in error_msg:
            return {
                "error": "session_closed",
                "message": "Browser session was unexpectedly closed",
                "resolution": "Session will be recreated on next request",
            }
        elif "Timeout" in error_msg and "linkedin.com" in error_msg:
            return {
                "error": "linkedin_timeout",
                "message": f"LinkedIn page took too long to load: {error_msg}",
                "resolution": "LinkedIn may be slow or blocking requests. Wait and retry.",
            }
        else:
            return {
                "error": "playwright_error",
                "message": f"Browser automation error: {error_msg}",
                "resolution": "Try again or check if LinkedIn is accessible",
            }

    # Handle general LinkedIn scraper errors
    elif isinstance(exception, LinkedInScraperError):
        return {
            "error": "linkedin_scraper_error",
            "message": str(exception),
            "resolution": "LinkedIn scraping encountered an error - try again or check your session",
        }

    # Handle legacy MCP errors
    elif isinstance(exception, LinkedInMCPError):
        return {"error": "linkedin_error", "message": str(exception)}

    else:
        # Generic error handling with enhanced logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Error in {context}: {exception}",
            extra={
                "context": context,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            },
        )
        return {
            "error": "unknown_error",
            "message": f"Failed to execute {context}: {str(exception)}",
            "resolution": "Check logs for more details and try again",
        }


def convert_exception_to_list_response(
    exception: Exception, context: str = ""
) -> List[Dict[str, Any]]:
    """
    Convert an exception to a list-formatted structured MCP response.

    Some tools return lists, so this provides the same error handling
    but wrapped in a list format.

    Args:
        exception: The exception to convert
        context: Additional context about where the error occurred

    Returns:
        List containing single structured error response dictionary
    """
    return [convert_exception_to_response(exception, context)]


async def safe_get_session():
    """
    Safely get or create a LinkedIn session with proper error handling.

    Returns:
        LinkedInSession: Authenticated session instance

    Raises:
        LinkedInMCPError: If session initialization fails
    """
    from linkedin_mcp_server.authentication import ensure_authentication
    from linkedin_mcp_server.session.manager import PlaywrightSessionManager

    # Get authentication first
    authentication = ensure_authentication()

    # Create session with authentication
    session = await PlaywrightSessionManager.get_or_create_session(authentication)

    return session
