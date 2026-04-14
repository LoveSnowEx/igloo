from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from granian import Granian

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    server = Granian("main:app")
    server.serve()
