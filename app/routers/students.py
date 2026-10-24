from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.deps import AdminUser, CurrentUser, DbSession, commit_or_409, get_or_404
from app.models import Student
from app.schemas import Page, StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=Page[StudentOut])
def list_students(
    db: DbSession,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=100, description="Search by NIM or name")] = None,
    class_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    stmt = select(Student)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Student.nim.ilike(pattern), Student.full_name.ilike(pattern)))
    if class_name:
        stmt = stmt.where(Student.class_name == class_name)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Student.nim).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: DbSession, _: CurrentUser) -> Student:
    if db.scalar(select(Student.id).where(Student.nim == payload.nim)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Student with NIM {payload.nim} already exists")
    student = Student(**payload.model_dump())
    db.add(student)
    commit_or_409(db, f"Student with NIM {payload.nim} already exists")
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: DbSession, _: CurrentUser) -> Student:
    return get_or_404(db, Student, student_id, "Student")


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: DbSession, _: CurrentUser) -> Student:
    student = get_or_404(db, Student, student_id, "Student")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    commit_or_409(db, "Another student already uses that NIM")
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: DbSession, _: AdminUser) -> None:
    student = get_or_404(db, Student, student_id, "Student")
    db.delete(student)
    db.commit()
