FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt update && apt install -y python3 python3-pip

# Copy pyproject and install dependencies via pip (PEP 517)
COPY pyproject.toml /tmp/project/pyproject.toml
RUN pip3 install --no-cache-dir /tmp/project

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
