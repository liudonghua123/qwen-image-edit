"""Compatibility shim module for packaging.

Flit (when reading [project] metadata) expects a module matching the
normalized project name (dashes -> underscores). This file re-exports
the FastAPI `app` from `image_edit_server.py` so the project can be
installed as an editable package without restructuring the repo.
"""
from image_edit_server import app  # re-export app for packaging
