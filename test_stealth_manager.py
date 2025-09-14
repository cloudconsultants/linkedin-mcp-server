from linkedin_mcp_server.scraper.browser.stealth_manager import StealthManager


def test_stealth_manager_initialization():
    """Test that stealth manager initializes without playwright fallback"""
    manager = StealthManager()
    assert manager is not None
    print("✅ Stealth manager initializes")


# Note: We can't easily test browser functionality without running actual browser
# as it requires authentication and proper setup. The main test is that imports work.
