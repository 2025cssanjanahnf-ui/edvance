import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"


class SubmissionType(str, enum.Enum):
    ASSIGNMENT = "assignment"
    PROJECT = "project"


class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    EVALUATED = "Evaluated"
    NEEDS_REVISION = "Needs Revision"
    LATE = "Late"


class ProjectStatus(str, enum.Enum):
    PLANNING = "Planning"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    COMPLETED = "Completed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.STUDENT.value)
    department_or_major = Column(String(255), nullable=True)
    roll_or_employee_id = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    assignments = relationship("Assignment", back_populates="faculty", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="faculty", cascade="all, delete-orphan")
    project_memberships = relationship("ProjectMember", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    feedbacks_given = relationship("Feedback", back_populates="faculty")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    course_code = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    faculty_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    deadline = Column(DateTime, nullable=False)
    max_score = Column(Integer, default=100)
    reference_file_path = Column(String(500), nullable=True)
    reference_file_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    faculty = relationship("User", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    course_code = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    faculty_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String(50), default=ProjectStatus.PLANNING.value)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    faculty = relationship("User", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_role = Column(String(100), default="Contributor")
    joined_at = Column(DateTime, default=utc_now)

    __table_args__ = (UniqueConstraint("project_id", "student_id", name="_project_student_uc"),)

    # Relationships
    project = relationship("Project", back_populates="members")
    student = relationship("User", back_populates="project_memberships")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    submission_type = Column(String(50), nullable=False)  # "assignment" or "project"
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(String(50), nullable=False)
    status = Column(String(50), default=SubmissionStatus.SUBMITTED.value)
    submitted_at = Column(DateTime, default=utc_now)

    # Relationships
    assignment = relationship("Assignment", back_populates="submissions")
    project = relationship("Project", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    feedback = relationship("Feedback", back_populates="submission", uselist=False, cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False)
    faculty_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=True)
    comments = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    submission = relationship("Submission", back_populates="feedback")
    faculty = relationship("User", back_populates="feedbacks_given")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    user = relationship("User", back_populates="notifications")

