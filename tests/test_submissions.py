import io
import pytest
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


def test_student_submit_assignment_file(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")

    # Mock file upload
    fake_file = io.BytesIO(b"%PDF-1.4 Mock Assignment Solution Document Content")

    res = client.post(
        "/api/submissions/assignment/1",
        headers={"Authorization": f"Bearer {student_token}"},
        data={"title": "Raft Consensus Key-Value Implementation Report"},
        files={"file": ("raft_report.pdf", fake_file, "application/pdf")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Raft Consensus Key-Value Implementation Report"
    assert data["submission_type"] == "assignment"
    assert data["file_type"] == ".pdf"


def test_reject_unauthorized_file_extension(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    fake_file = io.BytesIO(b"MZ executable content")

    res = client.post(
        "/api/submissions/assignment/1",
        headers={"Authorization": f"Bearer {student_token}"},
        data={"title": "Malicious Executable"},
        files={"file": ("danger.exe", fake_file, "application/x-msdownload")},
    )
    assert res.status_code == 400
    assert "not allowed" in res.json()["detail"]


def test_faculty_evaluate_submission(client):
    faculty_token = get_token(client, "faculty@edvance.edu", "Faculty@123", "faculty")

    # Evaluate submission 1 (already pre-seeded in test DB)
    res = client.post(
        "/api/feedback",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "submission_id": 1,
            "score": 98.5,
            "comments": "Superb architectural design and clean documentation.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["score"] == 98.5
    assert "Superb" in data["comments"]


def test_student_cannot_evaluate_submission(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    res = client.post(
        "/api/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "submission_id": 1,
            "score": 100,
            "comments": "Self evaluation should fail.",
        },
    )
    assert res.status_code == 403
    assert "Faculty privileges required" in res.json()["detail"]


def test_student_view_submission_feedback(client):
    student_token = get_token(client, "student@edvance.edu", "Student@123", "student")
    res = client.get(
        "/api/submissions/1",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    sub = res.json()
    assert sub["feedback"] is not None
    assert sub["feedback"]["score"] is not None
