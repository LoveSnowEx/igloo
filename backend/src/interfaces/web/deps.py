"""Web layer shared dependencies."""

from fastapi import Request
from fastapi.templating import Jinja2Templates


def is_htmx_request(request: Request) -> bool:
    """Check if the request was made by HTMX."""
    return request.headers.get("HX-Request") == "true"


def get_templates() -> Jinja2Templates:
    """Lazy-import to avoid circular dependencies."""
    from . import templates

    return templates
