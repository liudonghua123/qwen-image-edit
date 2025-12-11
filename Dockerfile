FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt update && apt install -y python3 python3-pip

RUN pip3 install fastapi uvicorn diffusers transformers accelerate pillow python-multipart python-dotenv torchvision

COPY image_edit_server.py /app/
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "image_edit_server:app", "--host", "0.0.0.0", "--port", "8000"]
