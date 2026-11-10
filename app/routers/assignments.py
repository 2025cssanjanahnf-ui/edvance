import os
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_faculty
from app.dependencies import validate_and_save_upload, BASE_DIR

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])


@router.get("", response_model=List[schemas.AssignmentOut])
def get_assignments(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List assignments. Students see all assignments with their own submission status."""
    if current_user.role == models.UserRole.FACULTY.value:
        assignments = db.query(models.Assignment).filter(
            models.Assignment.faculty_id == current_user.id
        ).order_by(models.Assignment.deadline.asc()).all()
    else:
        assignments = db.query(models.Assignment).order_by(models.Assignment.deadline.asc()).all()

    result = []
    for a in assignments:
        faculty = db.query(models.User).filter(models.User.id == a.faculty_id).first()
        submission_count = db.query(models.Submission).filter(
            models.Submission.assignment_id == a.id
        ).count()

        student_sub = None
        has_sub = False
        if current_user.role == models.UserRole.STUDENT.value:
            sub = db.query(models.Submission).filter(
                models.Submission.assignment_id == a.id,
                models.Submission.student_id == current_user.id
            ).first()
            if sub:
                has_sub = True
                fb_out = None
                if sub.feedback:
                    fb_out = schemas.FeedbackOut(
                        id=sub.feedback.id,
                        submission_id=sub.feedback.submission_id,
                        faculty_id=sub.feedback.faculty_id,
                        faculty_name=sub.feedback.faculty.full_name if sub.feedback.faculty else "Faculty",
                        score=sub.feedback.score,
                        comments=sub.feedback.comments,
                        created_at=sub.feedback.created_at
                    )
                student_sub = schemas.SubmissionOut(
                    id=sub.id,
                    title=sub.title,
                    submission_type=sub.submission_type,
                    assignment_id=sub.assignment_id,
                    project_id=sub.project_id,
                    student_id=sub.student_id,
                    student_name=current_user.full_name,
                    file_path=sub.file_path,
                    file_name=sub.file_name,
                    file_size=sub.file_size,
                    file_type=sub.file_type,
                    status=sub.status,
                    submitted_at=sub.submitted_at,
                    feedback=fb_out
                )

        item = schemas.AssignmentOut(
            id=a.id,
            title=a.title,
            course_code=a.course_code,
            description=a.description,
            deadline=a.deadline,
            max_score=a.max_score,
            faculty_id=a.faculty_id,
            faculty_name=faculty.full_name if faculty else "Faculty Member",
            reference_file_name=a.reference_file_name,
            reference_file_path=a.reference_file_path,
            created_at=a.created_at,
            submission_count=submission_count,
            has_submitted=has_sub,
            student_submission=student_sub
        )
        result.append(item)

    return result


@router.get("/{assignment_id}", response_model=schemas.AssignmentOut)
def get_assignment_detail(
    assignment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve single assignment details."""
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    faculty = db.query(models.User).filter(models.User.id == a.faculty_id).first()
    submission_count = db.query(models.Submission).filter(models.Submission.assignment_id == a.id).count()

    student_sub = None
    has_sub = False
    if current_user.role == models.UserRole.STUDENT.value:
        sub = db.query(models.Submission).filter(
            models.Submission.assignment_id == a.id,
            models.Submission.student_id == current_user.id
        ).first()
        if sub:
            has_sub = True
            fb_out = None
            if sub.feedback:
                fb_out = schemas.FeedbackOut(
                    id=sub.feedback.id,
                    submission_id=sub.feedback.submission_id,
                    faculty_id=sub.feedback.faculty_id,
                    faculty_name=sub.feedback.faculty.full_name if sub.feedback.faculty else "Faculty",
                    score=sub.feedback.score,
                    comments=sub.feedback.comments,
                    created_at=sub.feedback.created_at
                )
            student_sub = schemas.SubmissionOut(
                id=sub.id,
                title=sub.title,
                submission_type=sub.submission_type,
                assignment_id=sub.assignment_id,
                project_id=sub.project_id,
                student_id=sub.student_id,
                student_name=current_user.full_name,
                file_path=sub.file_path,
                file_name=sub.file_name,
                file_size=sub.file_size,
                file_type=sub.file_type,
                status=sub.status,
                submitted_at=sub.submitted_at,
                feedback=fb_out
            )

    return schemas.AssignmentOut(
        id=a.id,
        title=a.title,
        course_code=a.course_code,
        description=a.description,
        deadline=a.deadline,
        max_score=a.max_score,
        faculty_id=a.faculty_id,
        faculty_name=faculty.full_name if faculty else "Faculty Member",
        reference_file_name=a.reference_file_name,
        reference_file_path=a.reference_file_path,
        created_at=a.created_at,
        submission_count=submission_count,
        has_submitted=has_sub,
        student_submission=student_sub
    )


@router.post("", response_model=schemas.AssignmentOut)
def create_assignment(
    title: str = Form(...),
    course_code: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    max_score: int = Form(100),
    reference_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Create assignment and optionally upload reference materials."""
    try:
        parsed_deadline = datetime.fromisoformat(deadline)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM)."
        )

    ref_path = None
    ref_name = None
    if reference_file and reference_file.filename:
        saved_rel_path, clean_name, _, _ = validate_and_save_upload(reference_file, "references")
        ref_path = saved_rel_path
        ref_name = clean_name

    assignment = models.Assignment(
        title=title.strip(),
        course_code=course_code.strip(),
        description=description.strip(),
        deadline=parsed_deadline,
        max_score=max_score,
        faculty_id=current_user.id,
        reference_file_path=ref_path,
        reference_file_name=ref_name
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    # Notify all students
    students = db.query(models.User).filter(models.User.role == models.UserRole.STUDENT.value).all()
    for s in students:
        notif = models.Notification(
            user_id=s.id,
            title=f"New Assignment: {assignment.title}",
            message=f"Dr. {current_user.full_name} posted a new assignment for {assignment.course_code}. Due: {assignment.deadline.strftime('%b %d, %Y')}.",
            link="/student/assignments"
        )
        db.add(notif)
    db.commit()

    return schemas.AssignmentOut(
        id=assignment.id,
        title=assignment.title,
        course_code=assignment.course_code,
        description=assignment.description,
        deadline=assignment.deadline,
        max_score=assignment.max_score,
        faculty_id=assignment.faculty_id,
        faculty_name=current_user.full_name,
        reference_file_name=assignment.reference_file_name,
        reference_file_path=assignment.reference_file_path,
        created_at=assignment.created_at,
        submission_count=0,
        has_submitted=False
    )


@router.put("/{assignment_id}", response_model=schemas.AssignmentOut)
def update_assignment(
    assignment_id: int,
    title: str = Form(...),
    course_code: str = Form(...),
    description: str = Form(...),
    deadline: str = Form(...),
    max_score: int = Form(100),
    reference_file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Update assignment."""
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    if a.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit assignments you created.")

    try:
        parsed_deadline = datetime.fromisoformat(deadline)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid deadline format.")

    a.title = title.strip()
    a.course_code = course_code.strip()
    a.description = description.strip()
    a.deadline = parsed_deadline
    a.max_score = max_score

    if reference_file and reference_file.filename:
        saved_rel_path, clean_name, _, _ = validate_and_save_upload(reference_file, "references")
        a.reference_file_path = saved_rel_path
        a.reference_file_name = clean_name

    db.commit()
    db.refresh(a)

    submission_count = db.query(models.Submission).filter(models.Submission.assignment_id == a.id).count()

    return schemas.AssignmentOut(
        id=a.id,
        title=a.title,
        course_code=a.course_code,
        description=a.description,
        deadline=a.deadline,
        max_score=a.max_score,
        faculty_id=a.faculty_id,
        faculty_name=current_user.full_name,
        reference_file_name=a.reference_file_name,
        reference_file_path=a.reference_file_path,
        created_at=a.created_at,
        submission_count=submission_count,
        has_submitted=False
    )


@router.delete("/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Delete assignment."""
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")

    if a.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete assignments you created.")

    db.delete(a)
    db.commit()
    return {"message": "Assignment deleted successfully."}


@router.get("/{assignment_id}/reference")
def download_reference_file(
    assignment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Authorized download of assignment reference file."""
    a = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not a or not a.reference_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference file not found.")

    full_path = (BASE_DIR / a.reference_file_path).resolve()
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on storage.")

    return FileResponse(
        path=str(full_path),
        filename=a.reference_file_name or "reference_document",
        media_type="application/octet-stream"
    )

