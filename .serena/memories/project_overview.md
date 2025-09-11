# LinkedIn MCP Server - Project Overview

## Purpose
MCP (Model Context Protocol) server that enables AI assistants like Claude to connect to LinkedIn for profile, company, and job data scraping. Provides secure authentication via LinkedIn cookies and Chrome WebDriver automation.

## Tech Stack
- **Language**: Python 3.12+
- **Server Framework**: FastMCP 2.10.1+
- **Web Automation**: Selenium WebDriver (Chrome)
- **Dependency Management**: UV package manager
- **Authentication**: LinkedIn session cookies stored in OS keychain
- **Type Checking**: ty
- **Linting/Formatting**: ruff
- **Pre-commit**: configured with hooks for code quality

## Key Dependencies
- `fastmcp>=2.10.1` - MCP server framework
- `linkedin-scraper` - Custom fork for LinkedIn data extraction
- `keyring>=25.6.0` - Secure credential storage
- `inquirer>=3.4.0` - Interactive CLI prompts
- `pyperclip>=1.9.0` - Clipboard operations

## Architecture Overview
### Core Components
1. **Authentication** (`authentication.py`) - LinkedIn credential management using system keychain
2. **WebDriver Management** (`drivers/chrome.py`) - Singleton pattern for Chrome WebDriver session management
3. **Server** (`server.py`) - FastMCP server implementation with tool registration
4. **CLI** (`cli_main.py`) - Three-phase startup: authentication → driver → server

### Tool Structure
All LinkedIn tools organized in `linkedin_mcp_server/tools/`:
- `person.py` - Profile scraping (`get_person_profile`)
- `company.py` - Company data extraction (`get_company_profile`)
- `job.py` - Job posting analysis (`get_job_details`, `search_jobs`, `get_recommended_jobs`)

### Transport Modes
- **stdio**: Default for local MCP clients (Claude Desktop)
- **streamable-http**: For web-based MCP clients and testing

### Authentication Flow
1. Credentials stored securely in OS keychain using `keyring` library
2. LinkedIn authentication via `li_at` session cookie
3. Automatic session validation and renewal
4. Chrome WebDriver automation handles browser interactions
