from patchright.async_api import Error, TimeoutError


def test_patchright_errors_available():
    """Verify error types are accessible from patchright"""
    assert Error is not None
    assert TimeoutError is not None


def test_error_handler_imports():
    """Verify error_handler.py imports work"""
    from linkedin_mcp_server.error_handler import handle_tool_error

    # Should not raise ImportError
    assert handle_tool_error is not None
