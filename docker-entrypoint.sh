#!/bin/bash
set -e

# Docker entrypoint for LinkedIn MCP Server
# Handles authentication setup for containerized environments

echo "🚀 Starting LinkedIn MCP Server in Docker..."

# Check if LinkedIn cookie is provided via environment variable
if [ -n "$LINKEDIN_COOKIE" ]; then
    echo "✅ LinkedIn cookie provided via environment variable"
    # The application will pick it up from the environment
else
    echo "⚠️  No LINKEDIN_COOKIE environment variable found"
    echo "Please provide LinkedIn cookie via:"
    echo "  docker run -e LINKEDIN_COOKIE='your_li_at_cookie' ..."
    echo ""
    echo "To get your LinkedIn cookie:"
    echo "  1. Login to LinkedIn in your browser"
    echo "  2. Open Developer Tools (F12)"
    echo "  3. Go to Application/Storage > Cookies"
    echo "  4. Find and copy the 'li_at' cookie value"
fi

# Execute the main application
exec python -m linkedin_mcp_server "$@"
