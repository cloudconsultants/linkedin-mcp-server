# Code Style and Conventions

## Code Formatting and Linting
- **Formatter**: ruff (configured in pre-commit)
- **Linter**: ruff with `--fix` flag for auto-fixes
- **Type Checker**: ty (local pre-commit hook)
- **Pre-commit hooks**: Enabled for trailing whitespace, YAML validation, merge conflicts, debug statements

## Python Style
- **Python Version**: 3.12+ required
- **Type Hints**: Used throughout codebase (ty type checking enforced)
- **Docstrings**: Function docstrings present, following standard Python conventions
- **Async/Await**: Used where appropriate (MCP tools are async)

## File Organization
- Clear separation of concerns:
  - `/tools/` - MCP tool implementations
  - `/drivers/` - WebDriver management
  - `/config/` - Configuration management
- Snake_case for modules and functions
- Clear imports organization

## Error Handling
- Custom exception hierarchy in `exceptions.py`
- Comprehensive error handling for:
  - LinkedIn rate limiting and security challenges
  - Invalid credentials and session expiration
  - Chrome WebDriver connection issues
  - Cookie extraction failures

## Logging
- Structured logging using Python logging module
- JSON format in non-interactive mode
- Different log levels supported (DEBUG, INFO, WARNING, ERROR)
- Logger instances named per module

## Configuration
- Environment variables: `LINKEDIN_COOKIE`, `CHROMEDRIVER_PATH`, `LOG_LEVEL`
- CLI flags support all major configuration options
- Secure credential storage using system keychain

## Import Style
- Standard library imports first
- Third-party imports second
- Local imports last
- Absolute imports preferred