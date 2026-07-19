"""Web page routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..deps import is_htmx_request, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the home page."""
    return templates.TemplateResponse(
        request=request,
        name="pages/index.html",
        context={"csrf_token": request.cookies.get("csrf_token", "")},
    )


@router.get("/welcome", response_class=HTMLResponse, response_model=None)
async def welcome(request: Request):
    """HTMX partial — returns a welcome fragment."""
    if is_htmx_request(request):
        return templates.TemplateResponse(
            request=request,
            name="partials/_welcome.html",
        )
    return RedirectResponse(url="/web/", status_code=302)
