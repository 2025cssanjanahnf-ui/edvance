from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user_optional, get_current_student

router = APIRouter(tags=["Student Portal"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def verify_student_access(request: Request, db: Session):
    """Helper to check student auth for HTML page routes, redirecting if unauthorized."""
    user = get_current_user_optional(request, db)
    if not user:
        return None, RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if user.role != models.UserRole.STUDENT.value:
        return None, RedirectResponse(url="/faculty/dashboard", status_code=status.HTTP_302_FOUND)
    return user, None


# --- HTML Template Routes ---

@router.get("/student/dashboard", response_class=HTMLResponse)
def student_dashboard_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/dashboard.html", context={
        "user": user,
        "title": "EDVANCE - Student Dashboard",
        "active_tab": "dashboard"
    })


@router.get("/student/assignments", response_class=HTMLResponse)
def student_assignments_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/assignments.html", context={
        "user": user,
        "title": "EDVANCE - Assignments",
        "active_tab": "assignments"
    })


@router.get("/student/projects", response_class=HTMLResponse)
def student_projects_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/projects.html", context={
        "user": user,
        "title": "EDVANCE - Projects",
        "active_tab": "projects"
    })


@router.get("/student/submissions", response_class=HTMLResponse)
def student_submissions_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/submissions.html", context={
        "user": user,
        "title": "EDVANCE - My Submissions",
        "active_tab": "submissions"
    })


@router.get("/student/feedback", response_class=HTMLResponse)
def student_feedback_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/feedback.html", context={
        "user": user,
        "title": "EDVANCE - Feedback",
        "active_tab": "feedback"
    })


@router.get("/student/profile", response_class=HTMLResponse)
def student_profile_page(request: Request, db: Session = Depends(get_db)):
    user, redirect = verify_student_access(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse(request=request, name="student/profile.html", context={
        "user": user,
        "title": "EDVANCE - Student Profile",
        "active_tab": "profile"
    })


# --- Student Dashboard API Data Endpoints ---

@router.get("/api/student/dashboard-stats")
def get_student_dashboard_stats(
    current_user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Provides key metrics, deadlines, and recent activities for student dashboard."""
    now = datetime.now(timezone.utc)

    # All assignments
    all_assignments = db.query(models.Assignment).all()
    # Student's submissions
    my_submissions = db.query(models.Submission).filter(
        models.Submission.student_id == current_user.id
    ).all()
    submitted_assignment_ids = {s.assignment_id for s in my_submissions if s.assignment_id}

    # Active assignments: deadline >= now and not yet submitted
    active_assignments = [
        a for a in all_assignments
        if (a.deadline.tzinfo is None and a.deadline >= datetime.now()) or
           (a.deadline.tzinfo is not None and a.deadline >= now)
    ]
    pending_submissions = [a for a in active_assignments if a.id not in submitted_assignment_ids]

    # Projects student is a member of
    my_memberships = db.query(models.ProjectMember).filter(
        models.ProjectMember.student_id == current_user.id
    ).all()
    project_ids = [m.project_id for m in my_memberships]
    my_projects = db.query(models.Project).filter(models.Project.id.in_(project_ids)).all() if project_ids else []
    ongoing_projects = [p for p in my_projects if p.status != "Completed"]

    # Evaluated submissions count / feedbacks received
    feedbacks_count = db.query(models.Feedback).join(models.Submission).filter(
        models.Submission.student_id == current_user.id
    ).count()

    # Upcoming deadlines (sorted by closest deadline)
    upcoming_deadlines = []
    for a in active_assignments:
        dl = a.deadline.isoformat() if hasattr(a.deadline, 'isoformat') else str(a.deadline)
        upcoming_deadlines.append({
            "id": a.id,
            "title": a.title,
            "course": a.course_code,
            "type": "Assignment",
            "deadline": dl,
            "is_submitted": a.id in submitted_assignment_ids,
            "url": "/student/assignments"
        })
    for p in ongoing_projects:
        dl = p.deadline.isoformat() if hasattr(p.deadline, 'isoformat') else str(p.deadline)
        upcoming_deadlines.append({
            "id": p.id,
            "title": p.title,
            "course": p.course_code,
            "type": "Project",
            "deadline": dl,
            "is_submitted": False,
            "url": "/student/projects"
        })

    upcoming_deadlines.sort(key=lambda x: x["deadline"])

    # Recent activities (last 5 events from submissions or feedback)
    recent_activities = []
    for sub in sorted(my_submissions, key=lambda s: s.submitted_at, reverse=True)[:5]:
        status_label = "Received Feedback" if sub.feedback else f"Status: {sub.status}"
        recent_activities.append({
            "id": sub.id,
            "title": sub.title,
            "type": sub.submission_type.capitalize(),
            "date": sub.submitted_at.strftime("%b %d, %Y - %H:%M"),
            "status": sub.status,
            "detail": f"Score: {sub.feedback.score}/100" if sub.feedback and sub.feedback.score is not None else status_label
        })

    return {
        "student_name": current_user.full_name,
        "department": current_user.department_or_major or "General Studies",
        "active_assignments_count": len(active_assignments),
        "ongoing_projects_count": len(ongoing_projects),
        "pending_submissions_count": len(pending_submissions),
        "feedback_received_count": feedbacks_count,
        "upcoming_deadlines": upcoming_deadlines[:6],
        "recent_activities": recent_activities
    }


@router.get("/api/student/calendar-events", response_model=List[schemas.CalendarEvent])
def get_student_calendar_events(
    current_user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Returns calendar markers for student assignments and projects."""
    events: List[schemas.CalendarEvent] = []

    # Assignments
    assignments = db.query(models.Assignment).all()
    for a in assignments:
        d_str = a.deadline.strftime("%Y-%m-%d")
        events.append(schemas.CalendarEvent(
            id=a.id,
            title=a.title,
            date=d_str,
            type="assignment",
            course_code=a.course_code,
            url="/student/assignments"
        ))

    # Assigned Projects
    memberships = db.query(models.ProjectMember).filter(
        models.ProjectMember.student_id == current_user.id
    ).all()
    proj_ids = [m.project_id for m in memberships]
    if proj_ids:
        projects = db.query(models.Project).filter(models.Project.id.in_(proj_ids)).all()
        for p in projects:
            d_str = p.deadline.strftime("%Y-%m-%d")
            events.append(schemas.CalendarEvent(
                id=p.id,
                title=p.title,
                date=d_str,
                type="project",
                course_code=p.course_code,
                url="/student/projects"
            ))

    return events
