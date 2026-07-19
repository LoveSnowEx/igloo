"""Jinja2 templates singleton — separated to avoid circular imports."""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
