from collections import Counter, defaultdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import distinct, func, select

from app.deps import AdminUser, CurrentUser, DbSession, commit_or_409, get_or_404
from app.models import Attendance, AttendanceStatus, Course, Enrollment, PracticumSession, Student
from app.schemas import (
    AttendanceSummary,
    AttendanceSummaryRow,
    CourseCreate,
    CourseOut,
    EnrollRequest,
    EnrollResult,
    StudentOut,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: DbSession, _: AdminUser) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    commit_or_409(db, f"Course {payload.code} already exists")
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
def list_courses(db: DbSession, _: CurrentUser) -> list[Course]:
    return list(db.scalars(select(Course).order_by(Course.code)))


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: DbSession, _: CurrentUser) -> Course:
    return get_or_404(db, Course, course_id, "Course")


@router.post("/{course_id}/enrollments", response_model=EnrollResult)
def enroll_students(course_id: int, payload: EnrollRequest, db: DbSession, _: CurrentUser) -> EnrollResult:
    get_or_404(db, Course, course_id, "Course")
    requested = set(payload.student_ids)

    found = set(db.scalars(select(Student.id).where(Student.id.in_(requested))))
    missing = sorted(requested - found)
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Students not found: {missing}")

    already = set(
        db.scalars(
            select(Enrollment.student_id).where(
                Enrollment.course_id == course_id, Enrollment.student_id.in_(requested)
            )
        )
    )
    new_ids = sorted(requested - already)
    db.add_all(Enrollment(course_id=course_id, student_id=sid) for sid in new_ids)
    commit_or_409(db, "Enrollment conflict, please retry")
    return EnrollResult(enrolled=len(new_ids), already_enrolled=len(already))


@router.get("/{course_id}/students", response_model=list[StudentOut])
def list_course_students(course_id: int, db: DbSession, _: CurrentUser) -> list[Student]:
    get_or_404(db, Course, course_id, "Course")
    stmt = (
        select(Student)
        .join(Enrollment, Enrollment.student_id == Student.id)
        .where(Enrollment.course_id == course_id)
        .order_by(Student.nim)
    )
    return list(db.scalars(stmt))


@router.get("/{course_id}/attendance-summary", response_model=AttendanceSummary)
def attendance_summary(
    course_id: int,
    db: DbSession,
    _: CurrentUser,
    threshold: Annotated[float, Query(ge=0, le=100, description="Minimum attendance rate (%)")] = 75.0,
) -> AttendanceSummary:
    """Per-student attendance recap.

    A session counts as held once any attendance has been recorded for it. Students with
    no record in a held session are counted as absent. Rate = (present + late) / held.
    """
    get_or_404(db, Course, course_id, "Course")

    held = db.scalar(
        select(func.count(distinct(Attendance.session_id)))
        .join(PracticumSession, Attendance.session_id == PracticumSession.id)
        .where(PracticumSession.course_id == course_id)
    ) or 0

    rows = db.execute(
        select(Attendance.student_id, Attendance.status, func.count())
        .join(PracticumSession, Attendance.session_id == PracticumSession.id)
        .where(PracticumSession.course_id == course_id)
        .group_by(Attendance.student_id, Attendance.status)
    ).all()
    counts: dict[int, Counter] = defaultdict(Counter)
    for student_id, att_status, n in rows:
        counts[student_id][att_status] += n

    students = list_course_students(course_id, db, _)
    result: list[AttendanceSummaryRow] = []
    for s in students:
        c = counts.get(s.id, Counter())
        present = c[AttendanceStatus.present]
        late = c[AttendanceStatus.late]
        excused = c[AttendanceStatus.excused]
        absent = max(held - present - late - excused, 0)
        rate = round((present + late) / held * 100, 1) if held else 0.0
        result.append(
            AttendanceSummaryRow(
                student_id=s.id,
                nim=s.nim,
                full_name=s.full_name,
                present=present,
                late=late,
                excused=excused,
                absent=absent,
                attendance_rate=rate,
                at_risk=held > 0 and rate < threshold,
            )
        )
    return AttendanceSummary(course_id=course_id, sessions_held=held, threshold=threshold, students=result)
