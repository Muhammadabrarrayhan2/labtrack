from fastapi import APIRouter

from app.config import get_settings
from app.deps import CurrentUser, DbSession, get_or_404
from app.models import LabReport, utcnow
from app.schemas import DownloadUrl, GradeRequest, ReportOut
from app.storage import get_storage

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: DbSession, _: CurrentUser) -> LabReport:
    return get_or_404(db, LabReport, report_id, "Report")


@router.get("/{report_id}/download-url", response_model=DownloadUrl)
def download_url(report_id: int, db: DbSession, _: CurrentUser) -> DownloadUrl:
    """Short-lived signed URL. The bucket itself stays private."""
    report = get_or_404(db, LabReport, report_id, "Report")
    url = get_storage().signed_url(report.object_key, settings.signed_url_minutes)
    return DownloadUrl(url=url, expires_in_seconds=settings.signed_url_minutes * 60)


@router.patch("/{report_id}/grade", response_model=ReportOut)
def grade_report(report_id: int, payload: GradeRequest, db: DbSession, user: CurrentUser) -> LabReport:
    report = get_or_404(db, LabReport, report_id, "Report")
    report.score = payload.score
    report.feedback = payload.feedback
    report.graded_by = user.id
    report.graded_at = utcnow()
    db.commit()
    db.refresh(report)
    return report
