from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import AttendanceStatus, Role

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit
    role: Role = Role.assistant

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


# ---------- Students ----------
class StudentBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr | None = None
    class_name: str | None = Field(default=None, max_length=50)


class StudentCreate(StudentBase):
    nim: str = Field(pattern=r"^\d{8,15}$", description="Nomor Induk Mahasiswa, 8 to 15 digits")


class StudentUpdate(BaseModel):
    nim: str | None = Field(default=None, pattern=r"^\d{8,15}$")
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    class_name: str | None = Field(default=None, max_length=50)


class StudentOut(ORMModel):
    id: int
    nim: str
    full_name: str
    email: str | None
    class_name: str | None
    created_at: datetime


# ---------- Courses ----------
class CourseCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{3,20}$")
    name: str = Field(min_length=3, max_length=150)
    semester: str = Field(min_length=3, max_length=20, examples=["Ganjil 2026/2027"])


class CourseOut(ORMModel):
    id: int
    code: str
    name: str
    semester: str
    created_at: datetime


class EnrollRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1, max_length=500)


class EnrollResult(BaseModel):
    enrolled: int
    already_enrolled: int


# ---------- Sessions ----------
class SessionCreate(BaseModel):
    course_id: int
    session_no: int = Field(ge=1, le=30)
    title: str = Field(min_length=3, max_length=200)
    scheduled_at: datetime
    room: str | None = Field(default=None, max_length=50)


class SessionOut(ORMModel):
    id: int
    course_id: int
    session_no: int
    title: str
    scheduled_at: datetime
    room: str | None


# ---------- Attendance ----------
class AttendanceItem(BaseModel):
    student_id: int
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=255)


class AttendanceBulk(BaseModel):
    records: list[AttendanceItem] = Field(min_length=1, max_length=500)


class AttendanceOut(ORMModel):
    id: int
    session_id: int
    student_id: int
    status: AttendanceStatus
    note: str | None
    recorded_at: datetime


class AttendanceSummaryRow(BaseModel):
    student_id: int
    nim: str
    full_name: str
    present: int
    late: int
    excused: int
    absent: int
    attendance_rate: float
    at_risk: bool


class AttendanceSummary(BaseModel):
    course_id: int
    sessions_held: int
    threshold: float
    students: list[AttendanceSummaryRow]


# ---------- Reports ----------
class ReportOut(ORMModel):
    id: int
    session_id: int
    student_id: int
    original_filename: str
    size_bytes: int
    uploaded_at: datetime
    score: float | None
    feedback: str | None
    graded_at: datetime | None


class GradeRequest(BaseModel):
    score: float = Field(ge=0, le=100)
    feedback: str | None = Field(default=None, max_length=2000)


class DownloadUrl(BaseModel):
    url: str
    expires_in_seconds: int
