"""Web interface layer — Jinja2 templates + HTMX routes."""

from fastapi import APIRouter

from .deps import templates  # noqa: F401
from .routes.pages import router as pages_router

web_router = APIRouter(prefix="/web")
web_router.include_router(pages_router)
