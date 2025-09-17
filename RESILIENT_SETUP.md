# LinkedIn MCP Server Resilient Setup

This document explains the simplified resilient solution for handling BrokenPipeError issues with Claude Desktop.

## Problem

The LinkedIn MCP Server using FastMCP occasionally encounters `BrokenPipeError` when Claude Desktop disconnects unexpectedly. This happens in FastMCP's anyio TaskGroup during stdout flush operations and causes the server to crash.

## Solution: Simple Auto-Restart

Instead of complex HTTP proxies, we use a simple but intelligent auto-restart wrapper that:

1. **Automatically restarts** the server when it crashes
2. **Provides detailed logging** for troubleshooting
3. **Handles different failure types** intelligently
4. **Resets restart counters** after successful runs
5. **Prevents restart loops** with exponential backoff

## Usage

### Claude Desktop (Recommended)

The resilient launcher is already configured in your Claude Desktop config:

```json
{
  "mcpServers": {
    "linkedin-playwright": {
      "command": "/home/demian/MCPs/linkedin-mcp-server/run_linkedin_mcp_resilient.sh",
      "env": {
        "LOG_LEVEL": "WARNING",
        "LAZY_INIT": "true",
        "HEADLESS": "true",
        "USE_NEW_STEALTH": "true",
        "STEALTH_PROFILE": "NO_STEALTH"
      }
    }
  }
}
```

### Manual Testing

```bash
# Run with resilient auto-restart
./run_linkedin_mcp_resilient.sh

# Run HTTP server for testing (no auto-restart)
./run_linkedin_mcp_http.sh
```

## Features

### Intelligent Restart Logic

- **Max restarts**: 10 attempts before giving up
- **Success threshold**: 60 seconds - resets counter after successful run
- **Adaptive delays**: Exponential backoff for quick failures
- **Exit code analysis**: Different handling for different failure types

### Enhanced Logging

- **File logging**: `/tmp/linkedin_mcp_resilient.log`
- **Structured format**: Timestamps and log levels
- **Crash analysis**: Identifies BrokenPipeError vs other issues
- **Performance tracking**: Runtime duration monitoring

### BrokenPipeError Handling

- **Detection**: Recognizes exit code 32 as BrokenPipeError
- **Expected behavior**: Logs as warning, not error
- **Quick restart**: 2-second delay for pipe errors
- **No panic**: Treats disconnections as normal events

## Configuration

### Environment Variables

All standard LinkedIn MCP Server environment variables are supported:

```bash
# Core settings
LINKEDIN_COOKIE=your_cookie_here
LOG_LEVEL=WARNING
LAZY_INIT=true
HEADLESS=true

# Stealth configuration
USE_NEW_STEALTH=true
STEALTH_PROFILE=NO_STEALTH
```

### Resilient Launcher Settings

Configure in the script or via environment:

```bash
MAX_RESTARTS=10           # Maximum restart attempts
RESTART_DELAY=2           # Initial restart delay (seconds)
SUCCESS_THRESHOLD=60      # Reset counter after this many seconds
LOG_FILE=/tmp/linkedin_mcp_resilient.log  # Log file location
```

## Monitoring

### Check Status

```bash
# View real-time logs
tail -f /tmp/linkedin_mcp_resilient.log

# Check if server is running
ps aux | grep linkedin_mcp_server

# View recent Claude Desktop logs
tail -f ~/.config/Claude/logs/mcp-server-linkedin-playwright.log
```

### Log Analysis

The resilient launcher logs different event types:

- **INFO**: Normal startup, clean exit, successful runs
- **WARN**: BrokenPipeError, quick failures, configuration issues
- **ERROR**: Maximum restarts reached, fatal errors

## Troubleshooting

### Frequent Restarts

If you see frequent restarts in the logs:

1. **Check authentication**: Ensure `LINKEDIN_COOKIE` is valid
2. **Verify configuration**: Check environment variables
3. **Review logs**: Look for specific error patterns
4. **Test manually**: Run `uv run -m linkedin_mcp_server` directly

### No Auto-Restart

If restarts aren't happening:

1. **Check script permissions**: Ensure executable (`chmod +x`)
2. **Verify path**: Confirm script location in Claude config
3. **Test script**: Run manually to verify functionality

### Performance Issues

If server is slow to start:

1. **Check stealth profile**: `NO_STEALTH` is fastest
2. **Enable lazy init**: `LAZY_INIT=true` defers browser startup
3. **Monitor resources**: Check CPU/memory usage

## Benefits

### Over Complex HTTP Proxies

- **Simpler architecture**: Single script vs multiple components
- **Better compatibility**: Works with existing Claude Desktop config
- **Easier debugging**: Centralized logging and monitoring
- **Lower overhead**: No additional proxy processes

### Over Manual Restarts

- **Automatic recovery**: No user intervention needed
- **Intelligent behavior**: Adapts to different failure types
- **Detailed logging**: Better troubleshooting capabilities
- **Prevents loops**: Built-in safeguards against rapid restarts

## Files Removed

As part of this simplification, the following complex files were removed:

- `linkedin_mcp_http_proxy.py` - Unnecessary stdio proxy
- `run_linkedin_mcp_http_stable.sh` - Complex server manager
- `HTTP_TRANSPORT_SOLUTION.md` - Documentation for complex approach
- `claude_desktop_config_http.json` - Non-working HTTP config
- `run_linkedin_mcp_stable.sh` - Alternative Python wrapper approach

## Migration

If you were using any of the removed files:

1. **Update Claude Desktop config** to use `run_linkedin_mcp_resilient.sh`
2. **Remove references** to HTTP proxy files
3. **Test the resilient launcher** manually
4. **Monitor logs** for proper operation

The resilient launcher provides the same reliability benefits with much simpler architecture.
