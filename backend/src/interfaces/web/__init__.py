"""Web interface layer — Jinja2 templates + HTMX routes."""

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

from .routes.pages import router as pages_router

templates = Jinja2Templates(directory="templates")

web_router = APIRouter(prefix="/web")
web_router.include_router(pages_router)
