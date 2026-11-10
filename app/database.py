import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edvance.db")

# For SQLite, check_same_thread is needed for multi-threaded FastAPI workers
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_initial_data(db: Session):
    """Seed sample data if database is fresh."""
    from app.models import User, Assignment, Project, ProjectMember, Submission, Feedback, Notification
    from app.auth import get_password_hash

    # Check if data already exists
    if db.query(User).first():
        return

    # Create Users
    faculty = User(
        email="faculty@edvance.edu",
        hashed_password=get_password_hash("Faculty@123"),
        full_name="Dr. Eleanor Vance",
        role="faculty",
        department_or_major="Computer Science & Engineering",
        roll_or_employee_id="FAC-CS-101",
        bio="Professor of Computer Systems and Software Architecture with 12+ years of research and teaching experience."
    )
    student1 = User(
        email="student@edvance.edu",
        hashed_password=get_password_hash("Student@123"),
        full_name="Alex Rivera",
        role="student",
        department_or_major="Software Engineering",
        roll_or_employee_id="CS-2024-042",
        bio="Final year undergraduate passionate about full-stack web platforms and distributed microservices."
    )
    student2 = User(
        email="marcus@edvance.edu",
        hashed_password=get_password_hash("Student@123"),
        full_name="Marcus Chen",
        role="student",
        department_or_major="Data Science & AI",
        roll_or_employee_id="CS-2024-088",
        bio="AI enthusiast focused on deep learning pipelines and database performance tuning."
    )
    student3 = User(
        email="sarah@edvance.edu",
        hashed_password=get_password_hash("Student@123"),
        full_name="Sarah Jenkins",
        role="student",
        department_or_major="Cybersecurity",
        roll_or_employee_id="CS-2024-105",
        bio="Undergraduate researcher studying application security, auth architectures, and safe cloud infrastructure."
    )

    db.add_all([faculty, student1, student2, student3])
    db.commit()
    db.refresh(faculty)
    db.refresh(student1)
    db.refresh(student2)
    db.refresh(student3)

    # Create Initial Assignments
    now = datetime.now(timezone.utc)
    a1 = Assignment(
        title="Distributed Key-Value Store Architecture",
        course_code="CS401 - Cloud Architecture",
        description="Design and implement a replicated, fault-tolerant key-value store using raft consensus principles. Submit your architectural diagram, source code bundle, and comprehensive test suite report.",
        faculty_id=faculty.id,
        deadline=now + timedelta(days=5),
        max_score=100,
        reference_file_name="assignment1_specifications.pdf",
        reference_file_path="uploads/references/assignment1_specifications.pdf"
    )
    a2 = Assignment(
        title="High-Performance SQL Optimization & Indexing",
        course_code="CS302 - Database Systems",
        description="Analyze provided query execution plans on a 10M record dataset. Propose and implement composite index strategies, partitioning, and normalized view optimizations.",
        faculty_id=faculty.id,
        deadline=now + timedelta(days=12),
        max_score=100,
        reference_file_name="indexing_dataset_guide.pdf",
        reference_file_path="uploads/references/indexing_dataset_guide.pdf"
    )
    a3 = Assignment(
        title="Modern UI/UX Accessibility Audit & Redesign",
        course_code="CS210 - Human Computer Interaction",
        description="Conduct a full WCAG 2.1 AA audit on a target enterprise application. Document color contrast violations, ARIA role gaps, and provide complete revised layouts.",
        faculty_id=faculty.id,
        deadline=now - timedelta(days=2),  # Past deadline to test past/completed status
        max_score=100,
        reference_file_name="wcag_audit_template.docx",
        reference_file_path="uploads/references/wcag_audit_template.docx"
    )

    db.add_all([a1, a2, a3])
    db.commit()
    db.refresh(a1)
    db.refresh(a2)
    db.refresh(a3)

    # Create Initial Projects
    p1 = Project(
        title="Autonomous Drone Delivery Fleet Simulator",
        course_code="CS499 - Capstone Project",
        description="A real-time distributed simulation platform tracking autonomous aerial delivery drones with dynamic obstacle avoidance, battery logistics, and route optimization.",
        faculty_id=faculty.id,
        deadline=now + timedelta(days=25),
        status="In Progress"
    )
    p2 = Project(
        title="Privacy-Preserving Federated Medical Imaging",
        course_code="CS498 - Advanced Research",
        description="Developing a zero-knowledge federated learning framework allowing multiple healthcare institutions to train pneumonia detection models without sharing raw DICOM scans.",
        faculty_id=faculty.id,
        deadline=now + timedelta(days=40),
        status="Planning"
    )

    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    # Assign Project Members
    pm1 = ProjectMember(project_id=p1.id, student_id=student1.id, project_role="Team Lead & Backend Architect")
    pm2 = ProjectMember(project_id=p1.id, student_id=student2.id, project_role="Simulation Algorithm Engineer")
    pm3 = ProjectMember(project_id=p2.id, student_id=student1.id, project_role="Security & Cryptography Lead")
    pm4 = ProjectMember(project_id=p2.id, student_id=student3.id, project_role="ML Pipeline Developer")

    db.add_all([pm1, pm2, pm3, pm4])
    db.commit()

    # Create Sample Submissions
    sub1 = Submission(
        title="WCAG 2.1 AA Audit Report - Edvance Portal",
        submission_type="assignment",
        assignment_id=a3.id,
        project_id=None,
        student_id=student1.id,
        file_path="uploads/assignments/sample_audit_report.pdf",
        file_name="sample_audit_report.pdf",
        file_size=1024 * 340,
        file_type=".pdf",
        status="Evaluated",
        submitted_at=now - timedelta(days=3)
    )
    sub2 = Submission(
        title="Drone Fleet Simulator - Milestone 1 Architectural Spec",
        submission_type="project",
        assignment_id=None,
        project_id=p1.id,
        student_id=student1.id,
        file_path="uploads/projects/sample_fleet_architecture.pdf",
        file_name="sample_fleet_architecture.pdf",
        file_size=1024 * 780,
        file_type=".pdf",
        status="Submitted",
        submitted_at=now - timedelta(days=1)
    )

    db.add_all([sub1, sub2])
    db.commit()
    db.refresh(sub1)
    db.refresh(sub2)

    # Create Sample Feedback
    fb1 = Feedback(
        submission_id=sub1.id,
        faculty_id=faculty.id,
        score=96.0,
        comments="Outstanding accessibility analysis. Your focus states and keyboard navigation remediation strategies were particularly well thought out. Keep up the high standard!"
    )
    db.add(fb1)
    db.commit()

    # Create Sample Notifications
    n1 = Notification(
        user_id=student1.id,
        title="Grade & Feedback Published",
        message="Dr. Eleanor Vance evaluated your submission for 'Modern UI/UX Accessibility Audit'. Score: 96/100.",
        link="/student/feedback",
        is_read=False
    )
    n2 = Notification(
        user_id=student1.id,
        title="Upcoming Assignment Deadline",
        message="'Distributed Key-Value Store Architecture' is due in 5 days.",
        link="/student/assignments",
        is_read=False
    )
    n3 = Notification(
        user_id=faculty.id,
        title="New Project Milestone Submitted",
        message="Alex Rivera submitted 'Milestone 1 Architectural Spec' for Drone Delivery Fleet.",
        link="/faculty/submissions",
        is_read=False
    )
    db.add_all([n1, n2, n3])
    db.commit()


def init_db():
    """Initializes tables and seeds initial demo data safely."""
    from app import models  # Ensures models are imported before create_all
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

