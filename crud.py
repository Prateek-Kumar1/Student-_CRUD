"""All SQL lives here. Every query is parameterised (no string-built SQL values)."""
import sqlite3
from datetime import date
from typing import Optional

COLUMNS = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]


class DuplicateEmailError(Exception):
    pass


def _clean(data: dict) -> dict:
    out = {}
    for k in COLUMNS:
        v = data.get(k)
        out[k] = v.isoformat() if isinstance(v, date) else (str(v) if v is not None else None)
    return out


def _row(row: Optional[sqlite3.Row]) -> Optional[dict]:
    return dict(row) if row else None


def create_student(conn: sqlite3.Connection, data: dict) -> dict:
    vals = _clean(data)
    try:
        cur = conn.execute(
            f"INSERT INTO students ({', '.join(COLUMNS)}) VALUES ({', '.join('?' for _ in COLUMNS)})",
            [vals[c] for c in COLUMNS],
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "email" in str(e).lower():
            raise DuplicateEmailError(vals["email"])
        raise
    return get_student(conn, cur.lastrowid)


def get_student(conn: sqlite3.Connection, student_id: int) -> Optional[dict]:
    return _row(conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone())


def _where(name=None, course=None, email=None, dob_from=None, dob_to=None):
    clauses, params = [], []
    if name:
        clauses.append("name LIKE ? COLLATE NOCASE"); params.append(f"%{name}%")
    if course:
        clauses.append("course LIKE ? COLLATE NOCASE"); params.append(f"%{course}%")
    if email:
        clauses.append("email = ? COLLATE NOCASE"); params.append(email)
    if dob_from:
        clauses.append("date_of_birth >= ?"); params.append(dob_from.isoformat())
    if dob_to:
        clauses.append("date_of_birth <= ?"); params.append(dob_to.isoformat())
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def list_students(conn, *, name=None, course=None, email=None, dob_from=None, dob_to=None,
                  skip: int = 0, limit: int = 100) -> list[dict]:
    where, params = _where(name, course, email, dob_from, dob_to)
    rows = conn.execute(
        f"SELECT * FROM students{where} ORDER BY student_id LIMIT ? OFFSET ?",
        params + [limit, skip],
    ).fetchall()
    return [dict(r) for r in rows]


def count_students(conn, *, name=None, course=None, email=None, dob_from=None, dob_to=None) -> int:
    where, params = _where(name, course, email, dob_from, dob_to)
    return conn.execute(f"SELECT COUNT(*) FROM students{where}", params).fetchone()[0]


def distinct_courses(conn) -> list[str]:
    rows = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL").fetchall()
    return [r[0] for r in rows]


def update_student(conn, student_id: int, data: dict) -> Optional[dict]:
    """Replace all columns with `data` (caller merges for PATCH)."""
    if get_student(conn, student_id) is None:
        return None
    vals = _clean(data)
    try:
        conn.execute(
            f"UPDATE students SET {', '.join(c + ' = ?' for c in COLUMNS)} WHERE student_id = ?",
            [vals[c] for c in COLUMNS] + [student_id],
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "email" in str(e).lower():
            raise DuplicateEmailError(vals["email"])
        raise
    return get_student(conn, student_id)


def delete_student(conn, student_id: int) -> bool:
    cur = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    return cur.rowcount > 0
