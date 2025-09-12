# Suggested Commands for LinkedIn MCP Server

## Setup and Installation
```bash
# Install dependencies
uv sync
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install
```

## Development Commands
```bash
# Run pre-commit hooks (includes ruff linting and formatting)
uv run pre-commit run --all-files

# Run type checking
uv run ty check

# Run individual linting and formatting
uv run ruff check
uv run ruff format
```

## Running the Server
```bash
# Run server locally with visible browser (debugging)
uv run -m linkedin_mcp_server --no-headless --no-lazy-init

# Run with cookie from command line
uv run -m linkedin_mcp_server --cookie "li_at=YOUR_COOKIE_VALUE"

# Extract LinkedIn cookie interactively
uv run -m linkedin_mcp_server --get-cookie

# Run in HTTP mode for testing
uv run -m linkedin_mcp_server --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

## Docker Operations
```bash
# Build Docker image
docker build -t linkedin-mcp-server .

# Run with Docker
docker run -it --rm -e LINKEDIN_COOKIE="li_at=YOUR_COOKIE" linkedin-mcp-server
```

## Essential Commands When Task is Complete
1. **Linting**: `uv run ruff check --fix`
2. **Formatting**: `uv run ruff format`
3. **Type Checking**: `uv run ty check`
4. **Pre-commit**: `uv run pre-commit run --all-files`

## Testing Commands
Currently no specific test commands configured, but pytest is available in dev dependencies:
```bash
uv run pytest  # If tests exist
```
