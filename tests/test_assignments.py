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


def test_faculty_create_assignment(client):
    faculty_token = get_token(client, "faculty@edvance.edu", "Faculty@123", "faculty")
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()

    res = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {faculty_token}"},
        data={
            "title": "Quantum Computing Fundamentals",
            "course_code": "CS495",
            "description": "Implement Shor's algorithm simulation.",
            "deadline": future_deadline,
            "max_score": 100,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Quantum Computing Fundamentals"
    assert data["course_code"] == "CS495"


def test_student_cannot_create_assignment(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

    res = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {student_token}"},
        data={
            "title": "Unauthorized Assignment",
            "course_code": "CS101",
            "description": "This should be blocked.",
            "deadline": future_deadline,
            "max_score": 100,
        },
    )
    assert res.status_code == 403
    assert "Faculty privileges required" in res.json()["detail"]


def test_student_list_assignments(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    res = client.get(
        "/api/assignments",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 3


def test_faculty_delete_assignment(client):
    faculty_token = get_token(client, "faculty@edvance.edu", "Faculty@123", "faculty")
    # First create an assignment to delete
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    create_res = client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {faculty_token}"},
        data={
            "title": "Temporary Assignment",
            "course_code": "CS999",
            "description": "To be deleted.",
            "deadline": future_deadline,
            "max_score": 50,
        },
    )
    assign_id = create_res.json()["id"]

    # Delete assignment
    del_res = client.delete(
        f"/api/assignments/{assign_id}",
        headers={"Authorization": f"Bearer {faculty_token}"},
    )
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]


def test_student_cannot_delete_assignment(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    del_res = client.delete(
        "/api/assignments/1",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert del_res.status_code == 403
