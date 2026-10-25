from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import init_db
from .routers import ai, students


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Students Database CRUD API",
    description="FastAPI + SQLite student records, with an optional local Ollama Q&A endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(students.router)
app.include_router(ai.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs"}
