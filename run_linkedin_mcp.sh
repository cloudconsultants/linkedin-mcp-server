#!/bin/bash
set -e

# LinkedIn MCP Server Launch Script for Claude Desktop
# Updated to support .env files and better defaults

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

# Default arguments for Claude Desktop
DEFAULT_ARGS=""

# If no arguments provided, use stdio transport (default for Claude Desktop)
if [[ $# -eq 0 ]]; then
    DEFAULT_ARGS="--transport stdio"
fi

# Launch the LinkedIn MCP Server
echo "Starting LinkedIn MCP Server..." >&2
exec uv run -m linkedin_mcp_server $DEFAULT_ARGS "$@"
