# ====== STAGE 1: OPTIMIZED BUILDER ======
FROM python:3.12-slim AS builder

# Minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /build

# Copy project configuration
COPY pyproject.toml pyproject.toml

# Create virtual environment and install dependencies directly
RUN uv venv /build/.venv

# Install dependencies using pip install (more reliable than sync)
RUN uv pip install --no-cache-dir --refresh --python /build/.venv/bin/python \
    fastmcp>=2.10.1 \
    inquirer>=3.4.0 \
    keyring>=25.6.0 \
    pydantic>=2.11.7 \
    python-dotenv>=1.1.1 \
    rapidfuzz>=3.13.0 \
    pyperclip>=1.9.0 \
    patchright>=1.55.0 \
    fake-useragent>=1.4.0 \
    keyrings-alt>=5.0.2 \
    anyio==4.9.0

# Verify anyio installation is complete (should have _testing modules)
RUN /build/.venv/bin/python -c "from anyio.abc import TestRunner; from anyio._core._testing import TaskInfo, get_current_task; print('✅ anyio installation verified complete')"


# Install ONLY Chrome with --with-deps (ensure system integration)
RUN /build/.venv/bin/python -m patchright install chrome --with-deps

# Aggressive cleanup while preserving functionality
RUN find /build/.venv -name "*.pyc" -delete \
    && find /build/.venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /build/.venv -name "*.pyo" -delete \
    && find /build/.venv -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /build/.venv -name "test*" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /build/.venv -name "*test*.py" -delete \
    && rm -rf /build/.venv/lib/python3.12/site-packages/setuptools* \
    && rm -rf /build/.venv/lib/python3.12/site-packages/pip* \
    && rm -rf /build/.venv/lib/python3.12/site-packages/wheel*

# Clean browser installation
RUN find /root/.cache/ms-playwright -name "*.log" -delete \
    && find /root/.cache/ms-playwright -name "*.tmp" -delete \
    && find /root/.cache/ms-playwright -name "*debug*" -delete 2>/dev/null || true

# Pre-compile
RUN python -O -m compileall /build/.venv

# ====== STAGE 2: RUNTIME DEPS ======
FROM python:3.12-slim AS runtime-deps

# Core Chrome dependencies (optimized - removed rarely needed libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    # Essential Chrome dependencies only
    libnss3 \
    libatk-bridge2.0-0 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Skip: libxcomposite1, libxrandr2, libxkbcommon0 (graphics not essential for headless)
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y \
    && find /var/cache -type f -delete \
    && find /var/log -type f -delete 2>/dev/null || true

# Install Chrome with aggressive cleanup
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /usr/share/doc/* \
    && rm -rf /usr/share/man/* \
    && find /opt/google/chrome -name "*.debug" -delete 2>/dev/null || true

# ====== STAGE 3: RUNTIME ======
FROM runtime-deps AS runtime

# Minimal user setup
RUN useradd -m -u 1000 mcpuser \
    && mkdir -p /home/mcpuser/.local/share \
    && chown -R mcpuser:mcpuser /home/mcpuser/.local

WORKDIR /app

# Copy optimized Python environment
COPY --from=builder --chown=mcpuser:mcpuser /build/.venv /app/.venv

# Copy browser files
COPY --from=builder --chown=mcpuser:mcpuser /root/.cache/ms-playwright /home/mcpuser/.cache/ms-playwright

# Copy application
COPY --chown=mcpuser:mcpuser linkedin_mcp_server /app/linkedin_mcp_server
COPY --chown=mcpuser:mcpuser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Final cleanup
RUN find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

USER mcpuser

# Optimized environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=2 \
    PATCHRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    DOCKER_RUNTIME=1 \
    PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring

# Efficient health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=2 \
    CMD python -c "import linkedin_mcp_server; print('OK')" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD []
