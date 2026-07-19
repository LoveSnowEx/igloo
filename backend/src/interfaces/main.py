from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ..infrastructure.app_factory import create_application, lifespan_factory
from ..infrastructure.config.settings import get_settings
from ..infrastructure.security import validate_production_security
from ..interfaces.api import router
from .admin.initialize import create_admin_interface

settings = get_settings()


@asynccontextmanager
async def lifespan_with_security(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes security validation."""
    if settings.PRODUCTION_SECURITY_VALIDATION_ENABLED:
        validate_production_security(settings)

    default_lifespan = lifespan_factory(settings)

    async with default_lifespan(app):
        yield


app = create_application(
    router=router,
    settings=settings,
    lifespan=lifespan_with_security,
    create_tables_on_startup=None,
    enable_cors=None,
    cors_origins=None,
    enable_docs_in_production=None,
    docs_production_dependency=None,
    enable_gzip=None,
    openapi_prefix=None,
    title="igloo",
    summary="igloo — Fastro + HTMX + Alpine.js + Jinja2",
    description="""
    # igloo

    Built on Fastro — a modular FastAPI starter with:

    * Vertical-slice modules and a clean infrastructure layer
    * Session-based auth with OAuth providers
    * Swappable cache, queue, and rate-limit backends
    * HTMX + Alpine.js + Jinja2 server-rendered frontend
    * SQLAdmin admin UI
    """,
    version="0.2.0",
    contact={
        "name": "LoveSnowEx",
    },
    license_info={
        "name": "MIT",
        "identifier": "MIT",
    },
    openapi_tags=None,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
create_admin_interface(app)

app.mount("/static", StaticFiles(directory="static"), name="static")

from .web import web_router

app.include_router(web_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy"}


@app.get("/", tags=["Web"])
async def root():
    """Redirect root to the web interface."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/web/")
