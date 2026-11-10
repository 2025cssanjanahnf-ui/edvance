from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, get_current_faculty

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def format_project_out(p: models.Project, db: Session) -> schemas.ProjectOut:
    """Helper to convert Project model to detailed ProjectOut schema."""
    members_out = []
    for m in p.members:
        student = db.query(models.User).filter(models.User.id == m.student_id).first()
        if student:
            members_out.append(schemas.ProjectMemberOut(
                id=m.id,
                project_id=m.project_id,
                student_id=m.student_id,
                student_name=student.full_name,
                student_email=student.email,
                student_roll=student.roll_or_employee_id,
                project_role=m.project_role,
                joined_at=m.joined_at
            ))

    submissions_out = []
    for s in p.submissions:
        student = db.query(models.User).filter(models.User.id == s.student_id).first()
        fb_out = None
        if s.feedback:
            fb_out = schemas.FeedbackOut(
                id=s.feedback.id,
                submission_id=s.feedback.submission_id,
                faculty_id=s.feedback.faculty_id,
                faculty_name=s.feedback.faculty.full_name if s.feedback.faculty else "Faculty",
                score=s.feedback.score,
                comments=s.feedback.comments,
                created_at=s.feedback.created_at
            )
        submissions_out.append(schemas.SubmissionOut(
            id=s.id,
            title=s.title,
            submission_type=s.submission_type,
            assignment_id=s.assignment_id,
            project_id=s.project_id,
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
        ))

    faculty = db.query(models.User).filter(models.User.id == p.faculty_id).first()

    return schemas.ProjectOut(
        id=p.id,
        title=p.title,
        course_code=p.course_code,
        description=p.description,
        deadline=p.deadline,
        status=p.status,
        faculty_id=p.faculty_id,
        faculty_name=faculty.full_name if faculty else "Faculty Member",
        created_at=p.created_at,
        members=members_out,
        submissions=submissions_out
    )


@router.get("", response_model=List[schemas.ProjectOut])
def get_projects(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List projects based on user role."""
    if current_user.role == models.UserRole.FACULTY.value:
        projects = db.query(models.Project).filter(
            models.Project.faculty_id == current_user.id
        ).order_by(models.Project.deadline.asc()).all()
    else:
        # For students: projects they belong to or all assigned
        memberships = db.query(models.ProjectMember).filter(
            models.ProjectMember.student_id == current_user.id
        ).all()
        proj_ids = [m.project_id for m in memberships]
        projects = db.query(models.Project).filter(
            models.Project.id.in_(proj_ids)
        ).order_by(models.Project.deadline.asc()).all() if proj_ids else []

    return [format_project_out(p, db) for p in projects]


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project_detail(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details for a single project."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    # Authorization check for student
    if current_user.role == models.UserRole.STUDENT.value:
        is_member = db.query(models.ProjectMember).filter(
            models.ProjectMember.project_id == p.id,
            models.ProjectMember.student_id == current_user.id
        ).first()
        if not is_member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this project.")

    return format_project_out(p, db)


@router.post("", response_model=schemas.ProjectOut)
def create_project(
    data: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Create project and assign student members."""
    project = models.Project(
        title=data.title.strip(),
        course_code=data.course_code.strip(),
        description=data.description.strip(),
        deadline=data.deadline,
        status=data.status or "Planning",
        faculty_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Assign members if provided
    if data.member_ids:
        for sid in data.member_ids:
            student = db.query(models.User).filter(
                models.User.id == sid,
                models.User.role == models.UserRole.STUDENT.value
            ).first()
            if student:
                member = models.ProjectMember(
                    project_id=project.id,
                    student_id=student.id,
                    project_role="Contributor"
                )
                db.add(member)

                # Send notification
                notif = models.Notification(
                    user_id=student.id,
                    title=f"Assigned to Project: {project.title}",
                    message=f"You have been assigned to team project '{project.title}' ({project.course_code}).",
                    link="/student/projects"
                )
                db.add(notif)
        db.commit()
        db.refresh(project)

    return format_project_out(project, db)


@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: int,
    data: schemas.ProjectUpdate,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Update project."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if p.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit projects you created.")

    if data.title is not None:
        p.title = data.title.strip()
    if data.course_code is not None:
        p.course_code = data.course_code.strip()
    if data.description is not None:
        p.description = data.description.strip()
    if data.deadline is not None:
        p.deadline = data.deadline
    if data.status is not None:
        p.status = data.status

    db.commit()
    db.refresh(p)
    return format_project_out(p, db)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Delete project."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if p.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete projects you created.")

    db.delete(p)
    db.commit()
    return {"message": "Project deleted successfully."}


@router.post("/{project_id}/members", response_model=schemas.ProjectMemberOut)
def add_project_member(
    project_id: int,
    member_data: schemas.ProjectMemberAdd,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Add a student to a project team."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if p.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    student = db.query(models.User).filter(
        models.User.id == member_data.student_id,
        models.User.role == models.UserRole.STUDENT.value
    ).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    # Check already member
    existing = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.student_id == student.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is already a team member.")

    member = models.ProjectMember(
        project_id=project_id,
        student_id=student.id,
        project_role=member_data.project_role or "Contributor"
    )
    db.add(member)

    # Notify student
    notif = models.Notification(
        user_id=student.id,
        title=f"Added to Team: {p.title}",
        message=f"You have been added to '{p.title}' as {member.project_role}.",
        link="/student/projects"
    )
    db.add(notif)
    db.commit()
    db.refresh(member)

    return schemas.ProjectMemberOut(
        id=member.id,
        project_id=member.project_id,
        student_id=member.student_id,
        student_name=student.full_name,
        student_email=student.email,
        student_roll=student.roll_or_employee_id,
        project_role=member.project_role,
        joined_at=member.joined_at
    )


@router.delete("/{project_id}/members/{student_id}")
def remove_project_member(
    project_id: int,
    student_id: int,
    current_user: models.User = Depends(get_current_faculty),
    db: Session = Depends(get_db)
):
    """Faculty only: Remove student from project."""
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p or p.faculty_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    member = db.query(models.ProjectMember).filter(
        models.ProjectMember.project_id == project_id,
        models.ProjectMember.student_id == student_id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in project.")

    db.delete(member)
    db.commit()
    return {"message": "Member removed from project."}

