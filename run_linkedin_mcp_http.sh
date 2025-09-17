#!/bin/bash

# LinkedIn MCP Server HTTP Launch Script
# Uses HTTP transport to avoid BrokenPipeError issues with stdio

# Change to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if .env file exists and load it
if [[ -f ".env" ]]; then
    echo "Loading environment from .env file..." >&2
    set -a  # automatically export all variables
    source .env
    set +a
fi

# Default HTTP settings
DEFAULT_HOST="${MCP_HOST:-127.0.0.1}"
DEFAULT_PORT="${MCP_PORT:-8765}"
DEFAULT_PATH="${MCP_PATH:-/mcp}"

echo "Starting LinkedIn MCP Server (HTTP transport)..." >&2
echo "Server will be available at: http://${DEFAULT_HOST}:${DEFAULT_PORT}${DEFAULT_PATH}" >&2

# Launch with HTTP transport (streamable-http for Claude Desktop compatibility)
exec uv run -m linkedin_mcp_server \
    --transport streamable-http \
    --host "$DEFAULT_HOST" \
    --port "$DEFAULT_PORT" \
    --path "$DEFAULT_PATH" \
    "$@"
