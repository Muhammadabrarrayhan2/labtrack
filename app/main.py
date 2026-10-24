import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import DEFAULT_JWT_SECRET, get_settings
from app.database import Base, SessionLocal, engine
from app.logging_config import configure_logging
from app.models import Role, User
from app.routers import auth, courses, reports, sessions, students
from app.security import hash_password

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("labtrack")


def _bootstrap_admin() -> None:
    """Create the first admin from env vars (Secret Manager on Cloud Run) if it does not exist."""
    email = (settings.bootstrap_admin_email or "").strip().lower()
    password = settings.bootstrap_admin_password
    if not email or not password:
        return
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            return
        db.add(
            User(
                email=email,
                full_name="LabTrack Administrator",
                hashed_password=hash_password(password),
                role=Role.admin,
            )
        )
        try:
            db.commit()
            logger.info("Bootstrap admin created", extra={"user_id": email})
        except IntegrityError:
            db.rollback()  # another instance created it first


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env == "production" and settings.jwt_secret == DEFAULT_JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set in production")
    # Schema bootstrap. For schema changes after go-live, switch to Alembic migrations.
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    logger.info(f"LabTrack {__version__} started (env={settings.app_env})")
    yield


app = FastAPI(
    title="LabTrack API",
    description="Cloud-native practicum management API: students, sessions, attendance and lab reports.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def request_id_of(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(request: Request, status_code: int, detail, headers: dict | None = None) -> JSONResponse:
    """Error body shared by all handlers. Users quote request_id when reporting a problem,
    and support finds the matching log line with jsonPayload.request_id in Cloud Logging."""
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id_of(request)},
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, exc.detail, getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(request, 422, jsonable_encoder(exc.errors()))


@app.middleware("http")
async def access_log(request: Request, call_next):
    # Reuse the Cloud Run trace id so app logs line up with request logs in Cloud Logging
    trace = request.headers.get("x-cloud-trace-context", "")
    request_id = trace.split("/")[0] or uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled error",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        return error_response(request, 500, "Internal server error", {"X-Request-ID": request_id})

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    if response.status_code >= 500:
        level = logging.ERROR
    elif request.url.path == "/health":
        level = logging.DEBUG
    else:
        level = logging.INFO
    logger.log(
        level,
        f"{request.method} {request.url.path} {response.status_code}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


@app.get("/", tags=["ops"])
def root() -> dict:
    return {"service": "LabTrack API", "version": __version__, "docs": "/docs"}


@app.get("/health", tags=["ops"])
def health(request: Request):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed", extra={"request_id": request_id_of(request)})
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unreachable", "request_id": request_id_of(request)},
        )
    return {"status": "ok", "database": "ok", "version": __version__, "environment": settings.app_env}


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(courses.router)
app.include_router(sessions.router)
app.include_router(reports.router)

if not settings.gcs_bucket:
    # Development only: serve uploaded files from the local folder
    Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/local-files", StaticFiles(directory=settings.local_upload_dir), name="local-files")
