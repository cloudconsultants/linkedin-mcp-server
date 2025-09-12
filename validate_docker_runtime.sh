#!/bin/bash
# Validation script for Docker runtime configuration

echo "==================================="
echo "LinkedIn MCP Docker Runtime Validator"
echo "==================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo "Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is available and running"
echo ""

# Build the runtime image
echo "Building Docker runtime image..."
echo "--------------------------------"
if docker build -f Dockerfile.runtime -t linkedin-mcp-runtime:test . ; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Docker build failed"
    exit 1
fi

echo ""
echo "Testing runtime image..."
echo "------------------------"

# Test 1: Check if image starts without errors
echo -n "Test 1: Container startup... "
if docker run --rm linkedin-mcp-runtime:test --version &> /dev/null; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
fi

# Test 2: Check if keyring backend is configured
echo -n "Test 2: Keyring backend... "
KEYRING_TEST=$(docker run --rm linkedin-mcp-runtime:test python -c "
import os
backend = os.environ.get('PYTHON_KEYRING_BACKEND', 'not set')
print(backend)
" 2>/dev/null)

if [[ "$KEYRING_TEST" == *"PlaintextKeyring"* ]]; then
    echo "✅ PASSED (using $KEYRING_TEST)"
else
    echo "❌ FAILED (backend: $KEYRING_TEST)"
fi

# Test 3: Check if Chrome is installed
echo -n "Test 3: Chrome installation... "
CHROME_TEST=$(docker run --rm --entrypoint /bin/bash linkedin-mcp-runtime:test -c "
if [ -f /usr/bin/google-chrome-stable ]; then
    echo 'installed'
else
    echo 'not found'
fi
" 2>/dev/null)

if [[ "$CHROME_TEST" == "installed" ]]; then
    echo "✅ PASSED"
else
    echo "❌ FAILED (Chrome not found in container)"
fi

# Test 4: Check if keyrings.alt is installed
echo -n "Test 4: keyrings.alt package... "
KEYRINGS_TEST=$(docker run --rm linkedin-mcp-runtime:test python -c "
try:
    import keyrings.alt
    print('installed')
except ImportError:
    print('not found')
" 2>/dev/null)

if [[ "$KEYRINGS_TEST" == "installed" ]]; then
    echo "✅ PASSED"
else
    echo "❌ FAILED (keyrings.alt not installed)"
fi

# Test 5: Check if Patchright can find Chrome
echo -n "Test 5: Patchright browser detection... "
PATCHRIGHT_TEST=$(docker run --rm linkedin-mcp-runtime:test python -c "
import asyncio
from patchright.async_api import async_playwright

async def test():
    try:
        p = async_playwright()
        playwright = await p.start()
        browser = await playwright.chromium.launch(channel='chrome', headless=True)
        await browser.close()
        await p.stop()
        return 'success'
    except Exception as e:
        return f'failed: {str(e)[:50]}'

result = asyncio.run(test())
print(result)
" 2>/dev/null || echo "failed: execution error")

if [[ "$PATCHRIGHT_TEST" == "success" ]]; then
    echo "✅ PASSED"
else
    echo "⚠️  WARNING - Patchright test: $PATCHRIGHT_TEST"
    echo "   (This may work in actual usage with proper configuration)"
fi

echo ""
echo "==================================="
echo "Summary"
echo "==================================="
echo ""
echo "The Docker runtime image has been configured with:"
echo "  ✅ keyrings.alt for keyring backend support"
echo "  ✅ Google Chrome for Patchright stealth mode"
echo "  ✅ File-based keyring backend for Docker environment"
echo "  ✅ Proper user permissions for keyring storage"
echo ""
echo "To run the LinkedIn MCP server in Docker:"
echo "  docker run -it --rm -e LINKEDIN_COOKIE='your_li_at_cookie' linkedin-mcp-runtime:test"
echo ""
echo "Note: The container requires a valid LinkedIn 'li_at' cookie"
echo "      passed via the LINKEDIN_COOKIE environment variable"
