from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user_optional, get_current_faculty

router = APIRouter(tags=["Faculty Portal"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def verify_faculty_access(request: Request, db: Session):
    """Helper to check faculty auth for HTML page routes, redirecting if unauthorized."""
    user = get_current_user_optional(request, db)
    if not user:
        return None, RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if user.role != models.UserRole.FACULTY.value:
        return None, RedirectResponse(url="/student/dashboard", status_code=status.HTTP_302_FOUND)
    return user, None


# --- HTML Template Routes ---

@router.get("/faculty/dashboard", response_class=HTMLResponse)
def faculty_dashboard_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/dashboard.html", context={
        "user": user,
        "title": "EDVANCE - Faculty Dashboard",
        "active_tab": "dashboard"
    })


@router.get("/faculty/assignments", response_class=HTMLResponse)
def faculty_assignments_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/assignments.html", context={
        "user": user,
        "title": "EDVANCE - Assignment Management",
        "active_tab": "assignments"
    })


@router.get("/faculty/projects", response_class=HTMLResponse)
def faculty_projects_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/projects.html", context={
        "user": user,
        "title": "EDVANCE - Project Management",
        "active_tab": "projects"
    })


@router.get("/faculty/submissions", response_class=HTMLResponse)
def faculty_submissions_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/submissions.html", context={
        "user": user,
        "title": "EDVANCE - Student Submissions",
        "active_tab": "submissions"
    })


@router.get("/faculty/evaluation", response_class=HTMLResponse)
def faculty_evaluation_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/evaluation.html", context={
        "user": user,
        "title": "EDVANCE - Submission Evaluation",
        "active_tab": "evaluation"
    })


@router.get("/faculty/profile", response_class=HTMLResponse)
def faculty_profile_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_faculty_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="faculty/profile.html", context={
        "user": user,
        "title": "EDVANCE - Faculty Profile",
        "active_tab": "profile"
    })


# --- Faculty Dashboard API Data Endpoints ---

@router.get("/api/faculty/dashboard-stats")
def get_faculty_dashboard_stats(
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Metrics for faculty dashboard."""
    now = datetime.now(timezone.utc)

    # Assignments created by this faculty
    my_assignments = db.query(models.Assignment).filter(models.Assignment.faculty_id == current_user.id).all()
    assignment_ids = [a.id for a in my_assignments]

    # Projects created by this faculty
    my_projects = db.query(models.Project).filter(models.Project.faculty_id == current_user.id).all()
    project_ids = [p.id for p in my_projects]

    # Submissions under these assignments or projects
    submissions_query = db.query(models.Submission).filter(
        (models.Submission.assignment_id.in_(assignment_ids)) |
        (models.Submission.project_id.in_(project_ids))
    )
    all_submissions = submissions_query.all()
    pending_reviews = [s for s in all_submissions if s.status != "Evaluated"]

    # Recent submissions
    recent_submissions = []
    for sub in sorted(all_submissions, key=lambda s: s.submitted_at, reverse=True)[:6]:
        target_title = sub.assignment.title if sub.assignment else (sub.project.title if sub.project else "General")
        recent_submissions.append({
            "id": sub.id,
            "title": sub.title,
            "target": target_title,
            "student_name": sub.student.full_name if sub.student else "Unknown",
            "student_roll": sub.student.roll_or_employee_id if sub.student else "",
            "type": sub.submission_type.capitalize(),
            "date": sub.submitted_at.strftime("%b %d, %Y - %H:%M"),
            "status": sub.status,
            "file_name": sub.file_name,
            "has_feedback": sub.feedback is not None
        })

    # Upcoming deadlines
    upcoming_deadlines = []
    for a in my_assignments:
        dl = a.deadline.isoformat() if hasattr(a.deadline, 'isoformat') else str(a.deadline)
        upcoming_deadlines.append({
            "id": a.id,
            "title": a.title,
            "course": a.course_code,
            "type": "Assignment",
            "deadline": dl,
            "url": "/faculty/assignments"
        })
    for p in my_projects:
        dl = p.deadline.isoformat() if hasattr(p.deadline, 'isoformat') else str(p.deadline)
        upcoming_deadlines.append({
            "id": p.id,
            "title": p.title,
            "course": p.course_code,
            "type": "Project",
            "deadline": dl,
            "url": "/faculty/projects"
        })

    upcoming_deadlines.sort(key=lambda x: x["deadline"])

    return {
        "faculty_name": current_user.full_name,
        "department": current_user.department_or_major or "Academic Department",
        "active_assignments_count": len(my_assignments),
        "active_projects_count": len(my_projects),
        "pending_reviews_count": len(pending_reviews),
        "total_submissions_count": len(all_submissions),
        "recent_submissions": recent_submissions,
        "upcoming_deadlines": upcoming_deadlines[:6]
    }


@router.get("/api/faculty/students-list", response_model=List[schemas.UserOut])
def get_students_list(
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Returns list of students so faculty can assign them to projects."""
    students = db.query(models.User).filter(models.User.role == models.UserRole.STUDENT.value).all()
    return students


@router.get("/api/faculty/calendar-events", response_model=List[schemas.CalendarEvent])
def get_faculty_calendar_events(
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Returns calendar markers for faculty assignments and projects."""
    events: List[schemas.CalendarEvent] = []

    assignments = db.query(models.Assignment).filter(models.Assignment.faculty_id == current_user.id).all()
    for a in assignments:
        d_str = a.deadline.strftime("%Y-%m-%d")
        events.append(schemas.CalendarEvent(
            id=a.id,
            title=a.title,
            date=d_str,
            type="assignment",
            course_code=a.course_code,
            url="/faculty/assignments"
        ))

    projects = db.query(models.Project).filter(models.Project.faculty_id == current_user.id).all()
    for p in projects:
        d_str = p.deadline.strftime("%Y-%m-%d")
        events.append(schemas.CalendarEvent(
            id=p.id,
            title=p.title,
            date=d_str,
            type="project",
            course_code=p.course_code,
            url="/faculty/projects"
        ))

    return events
