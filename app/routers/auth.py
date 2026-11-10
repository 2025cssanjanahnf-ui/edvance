from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app import models, schemas
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_user_optional,
)

router = APIRouter(tags=["Authentication"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    """Renders login page or redirects if already authenticated."""
    current_user = get_current_user_optional(request, db)
    if current_user:
        if current_user.role == models.UserRole.FACULTY.value:
            return RedirectResponse(url="/faculty/dashboard", status_code=status.HTTP_302_FOUND)
        return RedirectResponse(url="/student/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "EDVANCE - Login"})


@router.get("/logout")
def logout_redirect(response: Response):
    """Logout endpoint that clears cookie and redirects to login."""
    res = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    res.delete_cookie(key="access_token", path="/")
    return res


@router.post("/api/auth/login", response_model=schemas.Token)
def login_api(credentials: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    """API endpoint for authenticating students and faculty."""
    user = db.query(models.User).filter(models.User.email == credentials.email.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Validate role matching
    if credentials.role and user.role != credentials.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account is registered as a {user.role.capitalize()}, not {credentials.role.capitalize()}."
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "user_id": user.id, "role": user.role, "email": user.email}
    )

    # Set secure HTTP-only cookie for seamless browser navigation
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=False,  # Accessible for JS client-side auth synchronization
        max_age=86400,
        path="/",
        samesite="lax",
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        full_name=user.full_name,
        user_id=user.id,
    )


@router.post("/api/auth/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token login for OpenAPI documentation."""
    user = db.query(models.User).filter(models.User.email == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id), "user_id": user.id, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/api/auth/logout")
def logout_api(response: Response):
    """API endpoint to logout and clear cookies."""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Successfully logged out."}


@router.get("/api/auth/me", response_model=schemas.UserOut)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    """Returns the authenticated user's profile."""
    return current_user


@router.put("/api/auth/profile", response_model=schemas.UserOut)
def update_profile(
    profile_data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows student or faculty to update their profile information."""
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name.strip()
    if profile_data.department_or_major is not None:
        current_user.department_or_major = profile_data.department_or_major.strip()
    if profile_data.roll_or_employee_id is not None:
        current_user.roll_or_employee_id = profile_data.roll_or_employee_id.strip()
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio.strip()
    if profile_data.password and len(profile_data.password.strip()) >= 6:
        current_user.hashed_password = get_password_hash(profile_data.password.strip())

    db.commit()
    db.refresh(current_user)
    return current_user
