"""Pydantic models: request validation and response shapes."""
import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,18}$")


class _StudentFields(BaseModel):
    @field_validator("name", "course", "address", check_fields=False, mode="before")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            return v.strip() or None
        return v

    @field_validator("date_of_birth", check_fields=False)
    @classmethod
    def _dob_not_future(cls, v):
        if v is not None and v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("phone", check_fields=False, mode="before")
    @classmethod
    def _phone_ok(cls, v):
        if v is None:
            return v
        v = str(v).strip()
        if not v:
            return None
        if not PHONE_RE.match(v):
            raise ValueError("phone must contain 7-15 digits, optionally with +, spaces, -, ()")
        return v


class StudentCreate(_StudentFields):
    """Used for POST and PUT (full record)."""
    name: str = Field(..., min_length=1, max_length=100, examples=["Aarav Sharma"])
    date_of_birth: date = Field(..., examples=["2004-05-17"])
    email: Optional[EmailStr] = Field(None, examples=["aarav@example.com"])
    phone: Optional[str] = Field(None, examples=["+91 98765 43210"])
    course: Optional[str] = Field(None, max_length=100, examples=["Python Backend"])
    address: Optional[str] = Field(None, max_length=250)
    enrollment_date: Optional[date] = None

    @model_validator(mode="after")
    def _need_contact(self):
        if not self.email and not self.phone:
            raise ValueError("at least one of email or phone is required")
        return self


class StudentUpdate(_StudentFields):
    """Used for PATCH (any subset of fields)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    course: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=250)
    enrollment_date: Optional[date] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["How many students are there?"])


class AskResponse(BaseModel):
    question: str
    answer: str
    ai_used: bool
    model: Optional[str] = None
    filters_applied: dict
    records_used: list[StudentOut]
