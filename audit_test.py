import os
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal, init_db
from app import models, schemas

def get_all_routes():
    all_routes = []
    for r in app.routes:
        if hasattr(r, "original_router"):
            for sub in r.original_router.routes:
                all_routes.append((list(sub.methods), sub.path))
        elif hasattr(r, "path"):
            all_routes.append((list(getattr(r, "methods", ["GET"])), r.path))
    return all_routes

def audit_templates():
    print("=== AUDIT 1: JINJA2 TEMPLATES & STATIC REFERENCES ===")
    templates_dir = Path("app/templates")
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    html_files = list(templates_dir.glob("**/*.html"))

    missing_assets = []
    compile_errors = []

    for html_file in html_files:
        rel_path = html_file.relative_to(templates_dir).as_posix()
        try:
            tmpl = env.get_template(rel_path)
        except Exception as e:
            compile_errors.append((rel_path, str(e)))

        content = html_file.read_text(encoding="utf-8")
        matches = re.findall(r'(?:href|src)=["\']/static/([^"\']+)["\']', content)
        for m in matches:
            target = Path("app/static") / m.split("?")[0]
            if not target.exists():
                missing_assets.append((rel_path, f"/static/{m}"))

    if compile_errors:
        print("✗ Jinja2 Compilation Errors found:", compile_errors)
    else:
        print(f"✓ All {len(html_files)} Jinja2 templates compile cleanly.")

    if missing_assets:
        print("✗ Missing Static Assets referenced in templates:", missing_assets)
    else:
        print("✓ All referenced static CSS and JS files exist on disk.")

def audit_routes():
    print("\n=== AUDIT 2: FASTAPI ROUTER REGISTRATION ===")
    routes = get_all_routes()
    print(f"Total endpoints registered across all routers: {len(routes)}")
    key_paths = [
        "/", "/login", "/logout",
        "/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/auth/profile",
        "/student/dashboard", "/student/assignments", "/student/projects",
        "/student/submissions", "/student/feedback", "/student/profile",
        "/faculty/dashboard", "/faculty/assignments", "/faculty/projects",
        "/faculty/submissions", "/faculty/evaluation", "/faculty/profile",
        "/api/assignments", "/api/projects", "/api/submissions",
        "/api/feedback", "/api/notifications"
    ]
    registered_paths = [r[1] for r in routes]
    missing = [kp for kp in key_paths if kp not in registered_paths]
    if missing:
        print("✗ Missing key routes:", missing)
    else:
        print(f"✓ All {len(key_paths)} key portal routes are registered.")

def audit_html_js_integration():
    print("\n=== AUDIT 3: FRONTEND HTML & JS INTEGRATION ===")
    js_dir = Path("app/static/js")
    js_files = list(js_dir.glob("*.js"))
    html_files = list(Path("app/templates").glob("**/*.html"))
    all_html_text = "\n".join([h.read_text(encoding="utf-8") for h in html_files])

    missing_ids = []
    for js_path in js_files:
        content = js_path.read_text(encoding="utf-8")
        ids = re.findall(r'getElementById\(["\']([^"\']+)["\']\)', content)
        for element_id in ids:
            if f'id="{element_id}"' not in all_html_text and f"id='{element_id}'" not in all_html_text:
                if f'id = "{element_id}"' not in content and f'id: "{element_id}"' not in content:
                    missing_ids.append((js_path.name, element_id))

    if missing_ids:
        print("Potential missing IDs in HTML:", missing_ids)
    else:
        print(f"✓ All DOM element IDs referenced in JS exist in HTML templates.")

def audit_end_to_end_client():
    print("\n=== AUDIT 4: END-TO-END CLIENT PERMISSIONS & ACCESS ===")
    init_db()
    client = TestClient(app)

    student_pages = [
        "/student/dashboard", "/student/assignments", "/student/projects",
        "/student/submissions", "/student/feedback", "/student/profile"
    ]
    for p in student_pages:
        res = client.get(p, follow_redirects=False)
        assert res.status_code == 302, f"Unauthenticated {p} should redirect to /login"
        assert "/login" in res.headers["location"]
    print("✓ All 6 student pages redirect unauthenticated users to /login.")

    faculty_pages = [
        "/faculty/dashboard", "/faculty/assignments", "/faculty/projects",
        "/faculty/submissions", "/faculty/evaluation", "/faculty/profile"
    ]
    for p in faculty_pages:
        res = client.get(p, follow_redirects=False)
        assert res.status_code == 302, f"Unauthenticated {p} should redirect to /login"
        assert "/login" in res.headers["location"]
    print("✓ All 6 faculty pages redirect unauthenticated users to /login.")

    # Student login & Cross-Role protection
    login_s = client.post("/api/auth/login", json={"email": "student@edvance.edu", "password": "Student@123", "role": "student"})
    assert login_s.status_code == 200
    s_cookie = login_s.headers.get("set-cookie")

    res_cross = client.get("/faculty/dashboard", headers={"Cookie": s_cookie}, follow_redirects=False)
    assert res_cross.status_code == 302
    assert "/student/dashboard" in res_cross.headers["location"]
    print("✓ Student attempting to access faculty dashboard is redirected to student dashboard.")

    res_api_cross = client.post("/api/assignments", headers={"Cookie": s_cookie}, data={"title": "Test", "course_code": "CS", "description": "D", "deadline": "2026-12-01T10:00"})
    assert res_api_cross.status_code == 403
    print("✓ Student cannot execute faculty API endpoints (returns 403 Forbidden).")

    # Faculty login & Cross-Role protection
    login_f = client.post("/api/auth/login", json={"email": "faculty@edvance.edu", "password": "Faculty@123", "role": "faculty"})
    assert login_f.status_code == 200
    f_cookie = login_f.headers.get("set-cookie")

    res_cross_f = client.get("/student/dashboard", headers={"Cookie": f_cookie}, follow_redirects=False)
    assert res_cross_f.status_code == 302
    assert "/faculty/dashboard" in res_cross_f.headers["location"]
    print("✓ Faculty attempting to access student dashboard is redirected to faculty dashboard.")

    # All 6 student HTML pages render 200 OK with student session
    for p in student_pages:
        r = client.get(p, headers={"Cookie": s_cookie})
        assert r.status_code == 200, f"Student page {p} failed to render: {r.status_code}"
    print("✓ All 6 student HTML pages render with 200 OK.")

    # All 6 faculty HTML pages render 200 OK with faculty session
    for p in faculty_pages:
        r = client.get(p, headers={"Cookie": f_cookie})
        assert r.status_code == 200, f"Faculty page {p} failed to render: {r.status_code}"
    print("✓ All 6 faculty HTML pages render with 200 OK.")

if __name__ == "__main__":
    audit_templates()
    audit_routes()
    audit_html_js_integration()
    audit_end_to_end_client()
