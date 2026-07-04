from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Quizz Code de la Route API")
app.include_router(health.router)


@app.get("/")
def root() -> dict:
    return {"service": "quizz-code-de-la-route", "status": "ok"}
