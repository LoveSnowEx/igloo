"""Web layer shared dependencies."""

from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def is_htmx_request(request: Request) -> bool:
    """Check if the request was made by HTMX."""
    return request.headers.get("HX-Request") == "true"
