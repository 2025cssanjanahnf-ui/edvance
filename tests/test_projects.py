import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db, seed_initial_data

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_initial_data(db)
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client, email, password, role):
    res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "role": role},
    )
    return res.json()["access_token"]


def test_faculty_create_project(client):
    faculty_token = get_token(client, "faculty@edvance.edu", "Faculty@123", "faculty")
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    res = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "title": "Decentralized Identity Verification",
            "course_code": "CS490",
            "description": "Zero-knowledge proof identity protocols.",
            "deadline": future_deadline,
            "status": "In Progress",
            "member_ids": [2, 3],  # Alex Rivera and Marcus Chen
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Decentralized Identity Verification"
    assert len(data["members"]) == 2


def test_student_cannot_create_project(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()

    res = client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Unauthorized Student Project",
            "course_code": "CS100",
            "description": "Blocked action.",
            "deadline": future_deadline,
        },
    )
    assert res.status_code == 403


def test_student_view_assigned_projects(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    res = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    projects = res.json()
    assert len(projects) >= 1
    # Check team members included
    assert len(projects[0]["members"]) >= 1


def test_add_and_remove_member(client):
    faculty_token = get_token(client, "faculty@edvance.edu", "Faculty@123", "faculty")

    # Add student 4 (Sarah Jenkins) to project 1
    add_res = client.post(
        "/api/projects/1/members",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={"student_id": 4, "project_role": "QA Engineer"},
    )
    assert add_res.status_code in [200, 400]  # 400 if already member

    # Remove student 4 from project 1
    rem_res = client.delete(
        "/api/projects/1/members/4",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert rem_res.status_code == 200
