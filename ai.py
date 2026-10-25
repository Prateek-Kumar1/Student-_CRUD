import sqlite3

from fastapi import APIRouter, Depends

from .. import ai_service
from ..database import get_db
from ..schemas import AskRequest, AskResponse

router = APIRouter(prefix="/ai", tags=["AI (optional, Ollama)"])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: sqlite3.Connection = Depends(get_db)):
    """Ask a natural-language question about the stored students."""
    return ai_service.answer_question(db, payload.question)
