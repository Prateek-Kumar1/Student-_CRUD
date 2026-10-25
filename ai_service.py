"""Optional Ollama extension.

Safety design: the model NEVER writes or runs SQL. The backend maps the question to a
small set of fixed, parameterised filters (name / course / birth year / count), fetches the
matching rows itself, and hands only those rows to the model as context.
"""
import json
import os
import re
import sqlite3
from datetime import date

import httpx

from . import crud

MAX_CONTEXT_RECORDS = 50


def ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:1b")


def plan_question(question: str, courses: list[str]) -> dict:
    """Turn a natural-language question into safe, fixed filters."""
    q = question.lower()
    plan: dict = {"count_only": bool(re.search(r"\b(how many|count|number of|total)\b", q))}

    m = re.search(r"born\s+(after|since|from)\s+(\d{4})", q)
    if m:
        y = int(m.group(2))
        plan["dob_from"] = date(y + 1, 1, 1) if m.group(1) == "after" else date(y, 1, 1)
    m = re.search(r"born\s+(before|until|till)\s+(\d{4})", q)
    if m:
        y = int(m.group(2))
        plan["dob_to"] = date(y - 1, 12, 31) if m.group(1) == "before" else date(y, 12, 31)
    m = re.search(r"born\s+in\s+(\d{4})", q)
    if m:
        y = int(m.group(1))
        plan["dob_from"], plan["dob_to"] = date(y, 1, 1), date(y, 12, 31)

    for c in sorted(courses, key=len, reverse=True):
        if c.lower() in q:
            plan["course"] = c
            break

    m = re.search(r"(?:named|called|name is)\s+([a-z][a-z .'-]{1,40})", q)
    if m:
        plan["name"] = re.sub(r"[?.!]+$", "", m.group(1)).strip()

    if plan.get("dob_from") and plan.get("dob_to") and plan["dob_from"] > plan["dob_to"]:
        plan["dob_from"], plan["dob_to"] = plan["dob_to"], plan["dob_from"]
    return plan


def _filters(plan: dict) -> dict:
    return {k: plan[k] for k in ("name", "course", "dob_from", "dob_to") if k in plan}


def call_ollama(system: str, user: str) -> str:
    resp = httpx.post(
        f"{ollama_url()}/api/chat",
        json={
            "model": ollama_model(),
            "stream": False,
            "options": {"temperature": 0},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _fallback_answer(plan: dict, total: int, records: list[dict]) -> str:
    if plan["count_only"]:
        return f"There are {total} matching student(s)."
    if not records:
        return "No students match that question."
    lines = [f"{r['name']} (id {r['student_id']}, born {r['date_of_birth']}, course: {r['course'] or 'n/a'})"
             for r in records]
    return f"Found {total} matching student(s):\n" + "\n".join(lines)


def answer_question(conn: sqlite3.Connection, question: str) -> dict:
    plan = plan_question(question, crud.distinct_courses(conn))
    f = _filters(plan)
    total = crud.count_students(conn, **f)
    records = crud.list_students(conn, **f, limit=MAX_CONTEXT_RECORDS)

    system = (
        "You are an assistant for a student records system. Answer ONLY using the DATABASE RESULT "
        "provided. Never invent students or numbers. If the result does not contain the answer, say so. "
        "Be concise."
    )
    context = {
        "total_matching_students": total,
        "records_shown": len(records),
        "records": [
            {k: r[k] for k in ("student_id", "name", "date_of_birth", "course", "enrollment_date")}
            for r in records
        ],
    }
    user = f"DATABASE RESULT:\n{json.dumps(context, indent=2)}\n\nQUESTION: {question}"

    ai_used, model = True, ollama_model()
    try:
        answer = call_ollama(system, user)
    except Exception:
        ai_used, model = False, None
        answer = _fallback_answer(plan, total, records) + "\n(Ollama unavailable - answered directly from the database.)"

    return {
        "question": question,
        "answer": answer,
        "ai_used": ai_used,
        "model": model,
        "filters_applied": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in f.items()}
                           | {"count_only": plan["count_only"]},
        "records_used": records,
    }
