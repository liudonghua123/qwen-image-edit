"""ASGI entrypoint for uvicorn/gunicorn.

Reads common runtime settings from environment variables so running
`python main.py` respects container / user configuration.
"""
import os
from image_edit_server import app


def env_bool(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")
    reload = env_bool("RELOAD", False)

    uvicorn.run("image_edit_server:app", host=host, port=port, log_level=log_level, reload=reload)

