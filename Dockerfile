FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt update && apt install -y \
    python3 \
    python3-pip \
    build-essential \
    git \
    curl \
    libsndfile1 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject and install dependencies via pip (PEP 517)
## Install runtime dependencies directly to avoid invoking build backends
# (Installing the project via PEP 517 triggers flit/setuptools; for Docker
# builds we prefer to install explicit runtime dependencies.)
# Copy project and use `uv` to sync dependencies from `pyproject.toml`

# Copy project into a build directory (avoid using /tmp/project)
COPY . /build/
WORKDIR /build

# Upgrade pip and install `uv` (project sync tool) so we can run `uv sync`
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN python3 -m pip install --no-cache-dir uv

# Use uv to sync/install declared runtime dependencies from pyproject.toml
# `uv sync` will resolve and install wheels; using it avoids manual pip lists
RUN uv sync || (echo "uv sync failed" && exit 1)

# Copy application files
COPY image_edit_server.py /app/
COPY main.py /app/
COPY entrypoint.sh /app/
WORKDIR /app
RUN chmod +x /app/entrypoint.sh

# Health check (uses PORT env) — increase start period to allow model warm-up
ENV PORT=8000
# Allow up to 10 minutes for model loading before health checks start
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD python3 -c "import requests, os; p=os.getenv('PORT','8000'); requests.get(f'http://localhost:{p}/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
