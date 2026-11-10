import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db, seed_initial_data

# In-memory test database
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


def test_student_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "student@edvance.edu", "password": "Student@123", "role": "student"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "student"
    assert data["full_name"] == "Alex Rivera"


def test_faculty_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "faculty@edvance.edu", "password": "Faculty@123", "role": "faculty"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "faculty"
    assert "Dr. Eleanor Vance" in data["full_name"]


def test_login_invalid_password(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "student@edvance.edu", "password": "WrongPassword!", "role": "student"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_role_mismatch(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "student@edvance.edu", "password": "Student@123", "role": "faculty"},
    )
    assert response.status_code == 403
    assert "registered as a Student" in response.json()["detail"]


def test_get_current_user_profile(client):
    # First login to get token
    login_res = client.post(
        "/api/auth/login",
        json={"email": "student@edvance.edu", "password": "Student@123", "role": "student"},
    )
    token = login_res.json()["access_token"]

    # Request /api/auth/me
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "student@edvance.edu"


def test_unauthenticated_profile_access(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
