import logging

import uvicorn
from fastapi import FastAPI

from src.logging_config import configure_logging

# configure logging globally
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/ping")
async def ping():
    return {"message": "pong"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
