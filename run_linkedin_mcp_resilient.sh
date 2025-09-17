#!/bin/bash

# LinkedIn MCP Server Resilient Launch Script for Claude Desktop
# Auto-restarts the server on crashes (like BrokenPipeError from FastMCP stdio transport)
# Provides detailed logging and intelligent restart behavior
#
# IMPORTANT: MCP Protocol Requirements
# - stdout: MUST contain ONLY MCP protocol messages (JSON-RPC)
# - stderr: Used for logs, debug output, and non-protocol messages
# - Never redirect stderr to stdout (no 2>&1) or it will break Claude Desktop

# Change to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
MAX_RESTARTS=10
RESTART_DELAY=2
SUCCESS_THRESHOLD=60  # Seconds - reset counter after successful run
LOG_FILE="/home/demian/.config/Claude/logs/linkedin_mcp_resilient.log"

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

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >&2
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Function to analyze exit code and determine crash reason
analyze_crash() {
    local exit_code="$1"
    local run_duration="$2"

    case $exit_code in
        32)
            return "BrokenPipeError (FastMCP stdio transport issue)"
            ;;
        1)
            if [[ $run_duration -lt 5 ]]; then
                return "Quick failure - likely authentication or configuration issue"
            else
                return "Runtime error after startup"
            fi
            ;;
        127)
            return "Command not found - check uv installation and path"
            ;;
        *)
            return "Unknown error (exit code: $exit_code)"
            ;;
    esac
}

# Function to run the server with monitoring
run_server() {
    local start_time=$(date +%s)
    log_message "INFO" "Starting LinkedIn MCP Server (resilient mode) with args: $DEFAULT_ARGS $*"

    # Run server - let stdout pass through cleanly for MCP protocol
    # stderr will be visible in terminal/logs but won't interfere with MCP
    uv run -m linkedin_mcp_server $DEFAULT_ARGS "$@"
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_message "INFO" "Server exited with code $exit_code after ${duration}s"

    # Analyze the crash if it wasn't a clean exit
    if [[ $exit_code -ne 0 && $exit_code -ne 130 && $exit_code -ne 143 ]]; then
        local crash_reason=$(analyze_crash $exit_code $duration)
        log_message "WARN" "Crash analysis: $crash_reason"
    fi

    return $exit_code
}

# Cleanup function
cleanup() {
    log_message "INFO" "Resilient launcher exiting (received signal or max attempts reached)"
    exit $1
}

# Set up signal handlers
trap 'cleanup 0' INT TERM

# Initialize variables
RESTART_COUNT=0
LAST_START_TIME=0

log_message "INFO" "LinkedIn MCP Resilient Launcher started (max restarts: $MAX_RESTARTS)"

while true; do
    START_TIME=$(date +%s)
    run_server "$@"
    EXIT_CODE=$?
    END_TIME=$(date +%s)
    RUN_DURATION=$((END_TIME - START_TIME))

    # If server exited cleanly (code 0), exit the wrapper
    if [[ $EXIT_CODE -eq 0 ]]; then
        log_message "INFO" "Server exited cleanly"
        exit 0
    fi

    # If interrupted by user (SIGINT/SIGTERM), exit
    if [[ $EXIT_CODE -eq 130 ]] || [[ $EXIT_CODE -eq 143 ]]; then
        log_message "INFO" "Server stopped by user (exit code: $EXIT_CODE)"
        exit $EXIT_CODE
    fi

    # Reset restart counter if server ran successfully for more than threshold
    if [[ $RUN_DURATION -gt $SUCCESS_THRESHOLD ]]; then
        if [[ $RESTART_COUNT -gt 0 ]]; then
            log_message "INFO" "Server ran successfully for ${RUN_DURATION}s, resetting restart counter"
            RESTART_COUNT=0
        fi
    fi

    # Increment restart counter
    RESTART_COUNT=$((RESTART_COUNT + 1))

    # Check if we've exceeded max restarts
    if [[ $RESTART_COUNT -ge $MAX_RESTARTS ]]; then
        log_message "ERROR" "Maximum restart attempts ($MAX_RESTARTS) reached. Giving up."
        exit 1
    fi

    # Special handling for known issues
    if [[ $EXIT_CODE -eq 32 ]]; then
        log_message "WARN" "BrokenPipeError detected - this is expected when Claude Desktop disconnects"
    elif [[ $RUN_DURATION -lt 5 ]]; then
        log_message "WARN" "Quick failure detected - possible configuration issue"
        # Increase delay for quick failures to avoid rapid restart loops
        RESTART_DELAY=$((RESTART_DELAY * 2))
        if [[ $RESTART_DELAY -gt 30 ]]; then
            RESTART_DELAY=30
        fi
    else
        # Reset delay for other types of failures
        RESTART_DELAY=2
    fi

    # Log the restart
    log_message "INFO" "Restarting server (attempt $RESTART_COUNT/$MAX_RESTARTS, delay: ${RESTART_DELAY}s)"
    sleep $RESTART_DELAY
done
