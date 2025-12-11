"""ASGI entrypoint for uvicorn/gunicorn."""
from image_edit_server import app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("image_edit_server:app", host="0.0.0.0", port=8000, log_level="info")
