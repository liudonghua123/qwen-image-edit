FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt update && apt install -y python3 python3-pip

RUN pip3 install fastapi uvicorn diffusers transformers accelerate pillow python-multipart

COPY image_edit_server.py /app/
WORKDIR /app

CMD ["uvicorn", "image_edit_server:app", "--host", "0.0.0.0", "--port", "8000"]
