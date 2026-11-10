from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_faculty

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


def format_feedback_out(fb: models.Feedback, db: Session) -> schemas.FeedbackOut:
    faculty = db.query(models.User).filter(models.User.id == fb.faculty_id).first()
    sub = fb.submission
    target = "Coursework"
    sub_title = ""
    sub_type = "assignment"
    file_name = ""

    if sub:
        sub_title = sub.title
        sub_type = sub.submission_type
        file_name = sub.file_name
        if sub.assignment:
            target = f"{sub.assignment.course_code} - {sub.assignment.title}"
        elif sub.project:
            target = f"{sub.project.course_code} - {sub.project.title}"

    return schemas.FeedbackOut(
        id=fb.id,
        submission_id=fb.submission_id,
        faculty_id=fb.faculty_id,
        faculty_name=faculty.full_name if faculty else "Faculty Member",
        score=fb.score,
        comments=fb.comments,
        submission_title=sub_title,
        submission_type=sub_type,
        course_or_target=target,
        file_name=file_name,
        created_at=fb.created_at
    )


@router.get("", response_model=List[schemas.FeedbackOut])
def get_feedback_list(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve list of feedback for current student or given by current faculty."""
    if current_user.role == models.UserRole.STUDENT.value:
        feedbacks = db.query(models.Feedback).join(models.Submission).filter(
            models.Submission.student_id == current_user.id
        ).order_by(models.Feedback.created_at.desc()).all()
    else:
        feedbacks = db.query(models.Feedback).filter(
            models.Feedback.faculty_id == current_user.id
        ).order_by(models.Feedback.created_at.desc()).all()

    return [format_feedback_out(f, db) for f in feedbacks]


@router.get("/submission/{submission_id}", response_model=Optional[schemas.FeedbackOut])
def get_submission_feedback(
    submission_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve feedback for a specific submission."""
    fb = db.query(models.Feedback).filter(models.Feedback.submission_id == submission_id).first()
    if not fb:
        return None
    return format_feedback_out(fb, db)


@router.post("", response_model=schemas.FeedbackOut)
def create_or_update_evaluation(
    data: schemas.FeedbackCreate,
    status_update: Optional[str] = "Evaluated",
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Evaluate submission with score, comments, and status update."""
    submission = db.query(models.Submission).filter(models.Submission.id == data.submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    # Check faculty ownership of assignment or project
    if submission.assignment and submission.assignment.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not teach this assignment.")
    if submission.project and submission.project.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not supervising this project.")

    existing_fb = db.query(models.Feedback).filter(models.Feedback.submission_id == data.submission_id).first()
    now = datetime.now(timezone.utc)

    if existing_fb:
        existing_fb.score = data.score
        existing_fb.comments = data.comments.strip()
        existing_fb.created_at = now
        feedback_obj = existing_fb
    else:
        feedback_obj = models.Feedback(
            submission_id=data.submission_id,
            faculty_id=current_user.id,
            score=data.score,
            comments=data.comments.strip(),
            created_at=now
        )
        db.add(feedback_obj)

    # Update submission status
    final_status = data.status_update or status_update or "Evaluated"
    submission.status = final_status
    db.commit()
    db.refresh(feedback_obj)

    # Notify student
    score_str = f"Score: {feedback_obj.score}/100" if feedback_obj.score is not None else ""
    target_name = submission.assignment.title if submission.assignment else (submission.project.title if submission.project else "work")
    notif = models.Notification(
        user_id=submission.student_id,
        title=f"Evaluation Published: {submission.title}",
        message=f"{current_user.full_name} evaluated your submission for '{target_name}'. {score_str}".strip(),
        link="/student/feedback"
    )
    db.add(notif)
    db.commit()

    return format_feedback_out(feedback_obj, db)


@router.put("/{feedback_id}", response_model=schemas.FeedbackOut)
def update_feedback(
    feedback_id: int,
    data: schemas.FeedbackUpdate,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Update existing feedback."""
    fb = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found.")

    if fb.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to edit this feedback.")

    if data.score is not None:
        fb.score = data.score
    if data.comments is not None:
        fb.comments = data.comments.strip()

    db.commit()
    db.refresh(fb)
    return format_feedback_out(fb, db)

