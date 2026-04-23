from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from granian import Granian
from granian.constants import Interfaces

from app.db.base import SessionDep


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.base import create_db_and_tables

    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/livez")
async def livez(session: SessionDep):
    return {}


if __name__ == "__main__":
    server = Granian("main:app", interface=Interfaces.ASGI)
    server.serve()
