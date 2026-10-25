import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import crud
from ..database import get_db
from ..schemas import StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["Students"])


def _not_found(student_id: int) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Student with id {student_id} not found")


def _dup(email) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, f"A student with email '{email}' already exists")


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        return crud.create_student(db, payload.model_dump())
    except crud.DuplicateEmailError as e:
        raise _dup(e)


@router.get("", response_model=list[StudentOut])
def list_students(
    name: Optional[str] = Query(None, description="Partial, case-insensitive name match"),
    course: Optional[str] = Query(None, description="Partial, case-insensitive course match"),
    email: Optional[str] = Query(None, description="Exact email match"),
    born_after: Optional[date] = Query(None, description="Date of birth on/after this date"),
    born_before: Optional[date] = Query(None, description="Date of birth on/before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
):
    return crud.list_students(db, name=name, course=course, email=email,
                              dob_from=born_after, dob_to=born_before, skip=skip, limit=limit)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if not student:
        raise _not_found(student_id)
    return student


@router.put("/{student_id}", response_model=StudentOut)
def replace_student(student_id: int, payload: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        student = crud.update_student(db, student_id, payload.model_dump())
    except crud.DuplicateEmailError as e:
        raise _dup(e)
    if not student:
        raise _not_found(student_id)
    return student


@router.patch("/{student_id}", response_model=StudentOut)
def patch_student(student_id: int, payload: StudentUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = crud.get_student(db, student_id)
    if not existing:
        raise _not_found(student_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields provided to update")
    for required in ("name", "date_of_birth"):
        if required in changes and changes[required] is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{required} cannot be null")
    merged = {**existing, **changes}
    if not merged.get("email") and not merged.get("phone"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "A student must keep at least one of email or phone")
    try:
        return crud.update_student(db, student_id, merged)
    except crud.DuplicateEmailError as e:
        raise _dup(e)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.delete_student(db, student_id):
        raise _not_found(student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
