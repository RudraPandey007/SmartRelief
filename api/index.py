"""
Vercel serverless entrypoint for the FastAPI backend.

This file is the entry point for Vercel's Python serverless runtime.
It adds the backend directory to sys.path so all app imports resolve correctly,
then re-exports the FastAPI `app` instance.
"""
import os
import sys

# Add the backend directory to Python's module search path
# so `from app.main import app` works from this location
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
