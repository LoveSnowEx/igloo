"""Web page routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import templates
from ..deps import is_htmx_request

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the home page."""
    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "csrf_token": request.cookies.get("csrf_token", ""),
        },
    )


@router.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request) -> HTMLResponse:
    """HTMX partial — returns a welcome fragment."""
    if is_htmx_request(request):
        return templates.TemplateResponse(
            "partials/_welcome.html",
            {"request": request},
        )
    return RedirectResponse(url="/", status_code=302)
