from fastapi import FastAPI
from granian import Granian

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    server = Granian("main:app")
    server.serve()
