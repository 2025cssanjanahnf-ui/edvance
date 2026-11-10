from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: str  # "student" or "faculty"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    department_or_major: Optional[str] = None
    roll_or_employee_id: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department_or_major: Optional[str] = None
    roll_or_employee_id: Optional[str] = None
    bio: Optional[str] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Feedback Schemas
class FeedbackBase(BaseModel):
    score: Optional[float] = None
    comments: str


class FeedbackCreate(FeedbackBase):
    submission_id: int
    status_update: Optional[str] = "Evaluated"


class FeedbackUpdate(BaseModel):
    score: Optional[float] = None
    comments: Optional[str] = None


class FeedbackOut(FeedbackBase):
    id: int
    submission_id: int
    faculty_id: int
    faculty_name: Optional[str] = None
    submission_title: Optional[str] = None
    submission_type: Optional[str] = None
    course_or_target: Optional[str] = None
    file_name: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Submission Schemas
class SubmissionOut(BaseModel):
    id: int
    title: str
    submission_type: str
    assignment_id: Optional[int] = None
    assignment_title: Optional[str] = None
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    student_id: int
    student_name: Optional[str] = None
    student_roll: Optional[str] = None
    file_path: str
    file_name: str
    file_size: int
    file_type: str
    status: str
    submitted_at: datetime
    feedback: Optional[FeedbackOut] = None
    model_config = ConfigDict(from_attributes=True)


# Assignment Schemas
class AssignmentBase(BaseModel):
    title: str
    course_code: str
    description: str
    deadline: datetime
    max_score: Optional[int] = 100


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    course_code: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_score: Optional[int] = None


class AssignmentOut(AssignmentBase):
    id: int
    faculty_id: int
    faculty_name: Optional[str] = None
    reference_file_name: Optional[str] = None
    reference_file_path: Optional[str] = None
    created_at: datetime
    submission_count: Optional[int] = 0
    has_submitted: Optional[bool] = False
    student_submission: Optional[SubmissionOut] = None
    model_config = ConfigDict(from_attributes=True)


# Project Schemas
class ProjectMemberOut(BaseModel):
    id: int
    project_id: int
    student_id: int
    student_name: str
    student_email: str
    student_roll: Optional[str] = None
    project_role: str
    joined_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectMemberAdd(BaseModel):
    student_id: int
    project_role: Optional[str] = "Contributor"


class ProjectBase(BaseModel):
    title: str
    course_code: str
    description: str
    deadline: datetime
    status: Optional[str] = "Planning"


class ProjectCreate(ProjectBase):
    member_ids: Optional[List[int]] = []


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    course_code: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None
    member_ids: Optional[List[int]] = None


class ProjectOut(ProjectBase):
    id: int
    faculty_id: int
    faculty_name: Optional[str] = None
    created_at: datetime
    members: List[ProjectMemberOut] = []
    submissions: List[SubmissionOut] = []
    model_config = ConfigDict(from_attributes=True)


# Notification Schemas
class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Calendar Event Schema
class CalendarEvent(BaseModel):
    id: int
    title: str
    date: str  # YYYY-MM-DD
    type: str  # "assignment" or "project"
    course_code: str
    url: str

