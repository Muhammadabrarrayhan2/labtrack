import re
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import AdminUser, CurrentUser, DbSession, commit_or_409, get_or_404
from app.models import (
    Attendance,
    Course,
    Enrollment,
    LabReport,
    PracticumSession,
    Student,
    utcnow,
)
from app.schemas import AttendanceBulk, AttendanceOut, ReportOut, SessionCreate, SessionOut
from app.storage import get_storage

router = APIRouter(prefix="/sessions", tags=["sessions"])
settings = get_settings()


def _ensure_enrolled(db: DbSession, course_id: int, student_ids: set[int]) -> None:
    enrolled = set(
        db.scalars(
            select(Enrollment.student_id).where(
                Enrollment.course_id == course_id, Enrollment.student_id.in_(student_ids)
            )
        )
    )
    missing = sorted(student_ids - enrolled)
    if missing:
        raise HTTPException(
            422, f"Students not enrolled in this course: {missing}"
        )


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, db: DbSession, _: AdminUser) -> PracticumSession:
    get_or_404(db, Course, payload.course_id, "Course")
    session = PracticumSession(**payload.model_dump())
    db.add(session)
    commit_or_409(db, f"Session {payload.session_no} already exists for this course")
    db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(db: DbSession, _: CurrentUser, course_id: int | None = None) -> list[PracticumSession]:
    stmt = select(PracticumSession).order_by(PracticumSession.course_id, PracticumSession.session_no)
    if course_id is not None:
        stmt = stmt.where(PracticumSession.course_id == course_id)
    return list(db.scalars(stmt))


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: DbSession, _: CurrentUser) -> PracticumSession:
    return get_or_404(db, PracticumSession, session_id, "Session")


# ---------- Attendance ----------
@router.put("/{session_id}/attendance", response_model=list[AttendanceOut])
def record_attendance(
    session_id: int, payload: AttendanceBulk, db: DbSession, user: CurrentUser
) -> list[Attendance]:
    """Bulk upsert. Sending the same payload twice gives the same result (idempotent)."""
    session = get_or_404(db, PracticumSession, session_id, "Session")
    ids = [r.student_id for r in payload.records]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate student_id in records")
    _ensure_enrolled(db, session.course_id, set(ids))

    existing = {
        a.student_id: a
        for a in db.scalars(
            select(Attendance).where(Attendance.session_id == session_id, Attendance.student_id.in_(ids))
        )
    }
    now = utcnow()
    for record in payload.records:
        att = existing.get(record.student_id)
        if att is None:
            att = Attendance(session_id=session_id, student_id=record.student_id)
            db.add(att)
        att.status = record.status
        att.note = record.note
        att.recorded_by = user.id
        att.recorded_at = now
    commit_or_409(db, "Attendance was updated concurrently, please retry")
    return list_attendance(session_id, db, user)


@router.get("/{session_id}/attendance", response_model=list[AttendanceOut])
def list_attendance(session_id: int, db: DbSession, _: CurrentUser) -> list[Attendance]:
    get_or_404(db, PracticumSession, session_id, "Session")
    stmt = select(Attendance).where(Attendance.session_id == session_id).order_by(Attendance.student_id)
    return list(db.scalars(stmt))


# ---------- Lab reports ----------
@router.post("/{session_id}/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def upload_report(
    session_id: int,
    db: DbSession,
    _: CurrentUser,
    student_id: Annotated[int, Form()],
    file: Annotated[UploadFile, File(description="Practicum report, PDF only")],
) -> LabReport:
    session = get_or_404(db, PracticumSession, session_id, "Session")
    student = get_or_404(db, Student, student_id, "Student")
    _ensure_enrolled(db, session.course_id, {student_id})

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Max file size is {settings.max_upload_mb} MB")
    # Check the file signature, not the client-provided content type
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are accepted")

    course_code = re.sub(r"[^A-Za-z0-9_-]", "_", session.course.code)
    key = f"reports/{course_code}/session-{session.session_no:02d}/{student.nim}-{uuid.uuid4().hex[:8]}.pdf"
    get_storage().upload(key, data, "application/pdf")

    report = db.scalar(
        select(LabReport).where(LabReport.session_id == session_id, LabReport.student_id == student_id)
    )
    if report is None:
        report = LabReport(session_id=session_id, student_id=student_id)
        db.add(report)
    # A re-upload replaces the previous submission and clears its grade
    report.object_key = key
    report.original_filename = (file.filename or "report.pdf")[:255]
    report.size_bytes = len(data)
    report.uploaded_at = utcnow()
    report.score = None
    report.feedback = None
    report.graded_by = None
    report.graded_at = None
    commit_or_409(db, "Report was uploaded concurrently, please retry")
    db.refresh(report)
    return report


@router.get("/{session_id}/reports", response_model=list[ReportOut])
def list_reports(session_id: int, db: DbSession, _: CurrentUser) -> list[LabReport]:
    get_or_404(db, PracticumSession, session_id, "Session")
    stmt = select(LabReport).where(LabReport.session_id == session_id).order_by(LabReport.student_id)
    return list(db.scalars(stmt))
