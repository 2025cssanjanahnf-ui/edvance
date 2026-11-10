import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db, get_db
from app.auth import get_current_user_optional
from app.routers import (
    auth,
    student,
    faculty,
    assignments,
    projects,
    submissions,
    feedback,
    notifications,
)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe database initialization on startup without dropping tables
    init_db()
    # Ensure upload directories exist
    upload_base = BASE_DIR.parent / "uploads"
    (upload_base / "assignments").mkdir(parents=True, exist_ok=True)
    (upload_base / "projects").mkdir(parents=True, exist_ok=True)
    (upload_base / "references").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="EDVANCE",
    description="Learn. Build. Submit. Grow. - Modern Academic Collaboration and Submission Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include Routers
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(faculty.router)
app.include_router(assignments.router)
app.include_router(projects.router)
app.include_router(submissions.router)
app.include_router(feedback.router)
app.include_router(notifications.router)


@app.get("/")
def root(request: Request):
    """Root redirect to appropriate portal or login."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = get_current_user_optional(request, db)
        if user:
            if user.role == "faculty":
                return RedirectResponse(url="/faculty/dashboard", status_code=status.HTTP_302_FOUND)
            return RedirectResponse(url="/student/dashboard", status_code=status.HTTP_302_FOUND)
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

