import os
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_student
from app.dependencies import validate_and_save_upload, BASE_DIR

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])


def format_sub_out(s: models.Submission, db: Session) -> schemas.SubmissionOut:
    """Helper to convert Submission model to detailed SubmissionOut."""
    student = db.query(models.User).filter(models.User.id == s.student_id).first()
    assignment = db.query(models.Assignment).filter(models.Assignment.id == s.assignment_id).first() if s.assignment_id else None
    project = db.query(models.Project).filter(models.Project.id == s.project_id).first() if s.project_id else None

    fb_out = None
    if s.feedback:
        faculty = db.query(models.User).filter(models.User.id == s.feedback.faculty_id).first()
        fb_out = schemas.FeedbackOut(
            id=s.feedback.id,
            submission_id=s.feedback.submission_id,
            faculty_id=s.feedback.faculty_id,
            faculty_name=faculty.full_name if faculty else "Faculty",
            score=s.feedback.score,
            comments=s.feedback.comments,
            created_at=s.feedback.created_at
        )

    return schemas.SubmissionOut(
        id=s.id,
        title=s.title,
        submission_type=s.submission_type,
        assignment_id=s.assignment_id,
        assignment_title=assignment.title if assignment else None,
        project_id=s.project_id,
        project_title=project.title if project else None,
        student_id=s.student_id,
        student_name=student.full_name if student else "Student",
        student_roll=student.roll_or_employee_id if student else "",
        file_path=s.file_path,
        file_name=s.file_name,
        file_size=s.file_size,
        file_type=s.file_type,
        status=s.status,
        submitted_at=s.submitted_at,
        feedback=fb_out
    )


@router.get("", response_model=List[schemas.SubmissionOut])
def list_submissions(
    submission_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    assignment_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve submissions based on role and filters."""
    query = db.query(models.Submission)

    if current_user.role == models.UserRole.STUDENT.value:
        query = query.filter(models.Submission.student_id == current_user.id)
    else:
        # Faculty: only submissions for their assignments or projects
        my_assignment_ids = [a.id for a in db.query(models.Assignment).filter(models.Assignment.faculty_id == current_user.id).all()]
        my_project_ids = [p.id for p in db.query(models.Project).filter(models.Project.faculty_id == current_user.id).all()]

        query = query.filter(
            or_(
                models.Submission.assignment_id.in_(my_assignment_ids),
                models.Submission.project_id.in_(my_project_ids)
            )
        )

    if submission_type:
        query = query.filter(models.Submission.submission_type == submission_type.lower())
    if status_filter:
        query = query.filter(models.Submission.status == status_filter)
    if assignment_id:
        query = query.filter(models.Submission.assignment_id == assignment_id)
    if project_id:
        query = query.filter(models.Submission.project_id == project_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Submission.title.ilike(search_pattern),
                models.Submission.file_name.ilike(search_pattern)
            )
        )

    submissions = query.order_by(models.Submission.submitted_at.desc()).all()
    return [format_sub_out(s, db) for s in submissions]


@router.get("/{submission_id}", response_model=schemas.SubmissionOut)
def get_submission_detail(
    submission_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View submission details with security checks."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    # Authorization
    if current_user.role == models.UserRole.STUDENT.value:
        if s.student_id != current_user.id:
            # Check if project teammate
            if s.project_id:
                is_member = db.query(models.ProjectMember).filter(
                    models.ProjectMember.project_id == s.project_id,
                    models.ProjectMember.student_id == current_user.id
                ).first()
                if not is_member:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    else:
        # Faculty
        if s.assignment and s.assignment.faculty_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        if s.project and s.project.faculty_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return format_sub_out(s, db)


@router.post("/assignment/{assignment_id}", response_model=schemas.SubmissionOut)
def submit_assignment(
    assignment_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Students only: Submit solution file for an assignment."""
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    # Check if student already submitted (allow re-submission by replacing or updating status)
    existing = db.query(models.Submission).filter(
        models.Submission.assignment_id == assignment_id,
        models.Submission.student_id == current_user.id
    ).first()

    saved_rel_path, clean_name, file_size, extension = validate_and_save_upload(file, "assignments")

    now = datetime.now(timezone.utc)
    deadline_utc = a.deadline.replace(tzinfo=timezone.utc) if a.deadline.tzinfo is None else a.deadline
    initial_status = "Late" if now > deadline_utc else "Submitted"

    if existing:
        # Update existing submission
        existing.title = title.strip()
        existing.file_path = saved_rel_path
        existing.file_name = clean_name
        existing.file_size = file_size
        existing.file_type = extension
        existing.status = initial_status
        existing.submitted_at = now
        submission = existing
    else:
        submission = models.Submission(
            title=title.strip(),
            submission_type="assignment",
            assignment_id=assignment_id,
            project_id=None,
            student_id=current_user.id,
            file_path=saved_rel_path,
            file_name=clean_name,
            file_size=file_size,
            file_type=extension,
            status=initial_status,
            submitted_at=now
        )
        db.add(submission)

    db.commit()
    db.refresh(submission)

    # Notify faculty
    notif = models.Notification(
        user_id=a.faculty_id,
        title=f"New Assignment Submission: {a.title}",
        message=f"{current_user.full_name} submitted work for '{a.title}'. Status: {initial_status}.",
        link="/faculty/submissions"
    )
    db.add(notif)
    db.commit()

    return format_sub_out(submission, db)


@router.post("/project/{project_id}", response_model=schemas.SubmissionOut)
def submit_project_document(
    project_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Students only: Upload a document/milestone archive for an assigned project."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    # Verify student is a team member
    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.student_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this project team.")

    saved_rel_path, clean_name, file_size, extension = validate_and_save_upload(file, "projects")

    now = datetime.now(timezone.utc)
    deadline_utc = p.deadline.replace(tzinfo=timezone.utc) if p.deadline.tzinfo is None else p.deadline
    initial_status = "Late" if now > deadline_utc else "Submitted"

    submission = models.Submission(
        title=title.strip(),
        submission_type="project",
        assignment_id=None,
        project_id=project_id,
        student_id=current_user.id,
        file_path=saved_rel_path,
        file_name=clean_name,
        file_size=file_size,
        file_type=extension,
        status=initial_status,
        submitted_at=now
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Notify faculty
    notif = models.Notification(
        user_id=p.faculty_id,
        title=f"Project Milestone Uploaded: {p.title}",
        message=f"{current_user.full_name} submitted '{submission.title}' for project '{p.title}'.",
        link="/faculty/submissions"
    )
    db.add(notif)
    db.commit()

    return format_sub_out(submission, db)


@router.get("/{submission_id}/download")
def download_submission_file(
    submission_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Secure, authorized file download."""
    s = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission record not found.")

    # Access control
    if current_user.role == models.UserRole.STUDENT.value:
        if s.student_id != current_user.id:
            # Teammate check
            if s.project_id:
                is_mem = db.query(models.ProjectMember).filter(
                    models.ProjectMember.project_id == s.project_id,
                    models.ProjectMember.student_id == current_user.id
                ).first()
                if not is_mem:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    else:
        # Faculty
        if s.assignment and s.assignment.faculty_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        if s.project and s.project.faculty_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    full_path = (BASE_DIR / s.file_path).resolve()
    if not full_path.exists():
        # Fallback check if it was a seed file or relative to uploads
        alt_path = (BASE_DIR / "uploads" / Path(s.file_path).name).resolve()
        if alt_path.exists():
            full_path = alt_path
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on storage disk.")

    return FileResponse(
        path=str(full_path),
        filename=s.file_name,
        media_type="application/octet-stream"
    )

