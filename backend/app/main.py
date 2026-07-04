import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import health

app = FastAPI(title="Quizz Code de la Route API")
app.include_router(health.router)

os.makedirs(settings.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/")
def root() -> dict:
    return {"service": "quizz-code-de-la-route", "status": "ok"}
