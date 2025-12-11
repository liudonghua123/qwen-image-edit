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

# Upgrade pip and install runtime dependencies via pip (global site-packages)
# We explicitly list runtime deps to avoid invoking build backends for the
# local package during the Docker build.
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN python3 -m pip install --no-cache-dir --prefer-binary \
    fastapi uvicorn[standard] python-dotenv diffusers transformers accelerate \
    Pillow python-multipart requests torch torchvision bitsandbytes

# Copy application files
COPY image_edit_server.py /app/
COPY main.py /app/
WORKDIR /app

# Health check (uses PORT env) — increase start period to allow model warm-up
ENV PORT=8000
# Allow up to 10 minutes for model loading before health checks start
HEALTHCHECK --interval=30s --timeout=10s --start-period=600s --retries=3 \
    CMD python3 -c "import requests, os; p=os.getenv('PORT','8000'); requests.get(f'http://localhost:{p}/health')" || exit 1

CMD ["python3", "main.py"]
