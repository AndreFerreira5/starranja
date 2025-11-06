import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.db.connection import auth_db_connect, auth_db_disconnect
from src.logging_config import configure_logging
from src.routes import auth

# configure logging globally
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await auth_db_connect()
    yield
    await auth_db_disconnect()


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/ping")
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
