from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from granian import Granian
from granian.constants import Interfaces

from app.db.base import SessionDep
from app.routers.api.crystal_of_atlan.enhance import (
    page_router,
)
from app.routers.api.crystal_of_atlan.enhance import (
    router as crystal_of_atlan_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.base import create_db_and_tables

    create_db_and_tables()
    if not Path("templates").is_dir():
        msg = "templates/ 目錄不存在，請確認工作目錄"
        raise FileNotFoundError(msg)
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount crystal-of-atlan routers
app.include_router(crystal_of_atlan_router)
app.include_router(page_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/livez")
async def livez(session: SessionDep):
    return {}


if __name__ == "__main__":
    server = Granian("app.main:app", interface=Interfaces.ASGI)
    server.serve()
