# EDVANCE

**Tagline:** *Learn. Build. Submit. Grow.*

EDVANCE is a modern, full-stack academic collaboration and submission platform connecting students and faculty. Designed with a clean SaaS aesthetic, EDVANCE streamlines coursework deliverables, student capstone projects, cross-functional teams, real file submissions, and faculty evaluations without ERP clutter.

---

## 🚀 Key Highlights & Capabilities

- **Role-Based Portals**: Dedicated, isolated workspaces for **Students** and **Faculty**.
- **Real File Upload Pipeline**: Secure document ingestion supporting PDF, DOCX, ZIP, PY, and CSV formats with extension verification and 25MB limits.
- **Academic Milestone Tracking**: Manage course assignments, project specifications, deadlines, and submission states (*Submitted*, *Under Review*, *Evaluated*, *Needs Revision*, *Late*).
- **Interactive Monthly Calendar**: Integrated directly into student and faculty dashboards with interactive date inspection and deadline markers.
- **Faculty Evaluation Suite**: Direct submission review, scoring (0–100), structured feedback comments, and automated student notification delivery.
- **Notifications Hub**: Real-time notifications for new assignments, project team assignments, submission receipts, and published grades.
- **Production-Ready DevOps**: Complete Docker, Docker Compose, and GitHub Actions CI workflow configurations.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, Modern CSS3 (Custom Design System), Vanilla JavaScript (ES6+), [Lucide Icons](https://lucide.dev/) |
| **Backend** | Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy 2.0](https://www.sqlalchemy.org/), [Pydantic v2](https://docs.pydantic.dev/) |
| **Authentication** | Cryptographic Bcrypt Hashing, Signed JWT Tokens (HS256), Dual Cookie & Bearer Header support |
| **Database** | SQLite (`edvance.db`) with relational integrity and automatic initial seeding |
| **DevOps & QA** | Docker, Docker Compose, GitHub Actions, Pytest, Starlette TestClient |

---

## 📁 Project Architecture

```
EDVANCE/
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entrypoint & static mount
│   ├── database.py              # SQLAlchemy engine, session maker & auto-seeding
│   ├── models.py                # ORM entities (User, Assignment, Project, Submission, etc.)
│   ├── schemas.py               # Pydantic validation & response models
│   ├── auth.py                  # Bcrypt hashing, JWT creation & role dependencies
│   ├── dependencies.py          # File upload validation & safe disk storage
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login, token, logout & profile update
│   │   ├── student.py           # Student page views, metrics & calendar events
│   │   ├── faculty.py           # Faculty views, supervision stats & student lists
│   │   ├── assignments.py       # CRUD assignments & reference file downloads
│   │   ├── projects.py          # CRUD projects & team member management
│   │   ├── submissions.py       # File submission uploads & authorized downloads
│   │   ├── feedback.py          # Faculty evaluations & student feedback
│   │   └── notifications.py     # Notification list & mark-as-read endpoints
│   │
│   ├── templates/
│   │   ├── login.html           # Unified login with role selector & demo buttons
│   │   ├── student/             # Student portal HTML templates
│   │   │   ├── dashboard.html
│   │   │   ├── assignments.html
│   │   │   ├── projects.html
│   │   │   ├── submissions.html
│   │   │   ├── feedback.html
│   │   │   └── profile.html
│   │   │
│   │   └── faculty/             # Faculty portal HTML templates
│   │       ├── dashboard.html
│   │       ├── assignments.html
│   │       ├── projects.html
│   │       ├── submissions.html
│   │       ├── evaluation.html
│   │       └── profile.html
│   │
│   └── static/
│       ├── css/
│       │   ├── style.css        # Core Design System, layout, forms, tables & modals
│       │   ├── student.css      # Student specific styling & feedback cards
│       │   └── faculty.css      # Faculty evaluation panels & member pickers
│       │
│       ├── js/
│       │   ├── main.js          # Lucide initialization, toasts & modal helpers
│       │   ├── auth.js          # Login form logic & instant demo autofill
│       │   ├── student.js       # Student dashboard loader & monthly calendar
│       │   ├── faculty.js       # Faculty dashboard loader & supervision calendar
│       │   ├── assignments.js   # Assignment creation, edit, submission modals
│       │   ├── projects.js      # Team project management & milestone uploads
│       │   ├── submissions.js   # Submission filters, downloads & evaluations
│       │   └── notifications.js # Live notification dropdown & mark-read triggers
│       │
│       └── images/
│
├── uploads/
│   ├── assignments/             # Student assignment submissions
│   ├── projects/                # Student project milestone files
│   └── references/              # Faculty assignment guides & rubrics
│
├── tests/
│   ├── test_auth.py             # Auth & RBAC validation tests
│   ├── test_assignments.py      # Assignment lifecycle & access control tests
│   ├── test_projects.py         # Collaborative project & roster tests
│   └── test_submissions.py     # File upload & evaluation verification tests
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated GitHub Actions test pipeline
│
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment configuration template
├── .gitignore                   # Version control ignore rules
├── Dockerfile                   # Container build spec
├── docker-compose.yml           # Multi-container orchestration
└── README.md                    # System documentation
```

---

## 🔑 Pre-Configured Demo Credentials

The database automatically initializes upon first startup with the following accounts and sample academic coursework:

| Role | Name | Email | Password |
|---|---|---|---|
| **Faculty** | Dr. Eleanor Vance | `faculty@edvance.edu` | `Faculty@123` |
| **Student** | Alex Rivera | `student@edvance.edu` | `Student@123` |
| **Student** | Marcus Chen | `marcus@edvance.edu` | `Student@123` |
| **Student** | Sarah Jenkins | `sarah@edvance.edu` | `Student@123` |

*Tip: The login page includes one-click demo autofill buttons for immediate testing.*

---

## 💻 Local Setup Instructions

### 1. Prerequisites
- Python 3.10+ installed
- Git installed

### 2. Clone Repository & Setup Virtual Environment
```bash
# Clone the repository
git clone <repository_url> edvance
cd edvance

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (cmd):
.\venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
# Copy sample configuration
cp .env.example .env
```

### 5. Start the Application Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
**`http://127.0.0.1:8000`** (automatically redirects to `/login` or your active portal session).

---

## 🐳 Docker Deployment

### Run with Docker Compose
```bash
docker compose up --build
```
Access the application at `http://localhost:8000`. Persistent database and uploaded files are preserved in named Docker volumes.

---

## 🧪 Running the Test Suite

EDVANCE includes a comprehensive test suite covering authentication, RBAC authorization, CRUD operations, and file validation:

```bash
# Run pytest with detailed verbose output
pytest tests/ -v
```

---

## 🌿 Recommended GitFlow Branching Strategy

- `main`: Production-ready release branch. Directly deployed to production environments.
- `develop`: Integration branch where completed features merge before release tagging.
- `feature/<feature-name>`: Feature branches branched off `develop` (e.g. `feature/canvas-lms-export`).
- `bugfix/<issue-name>`: Dedicated defect fixes during QA or staging validation.
- `hotfix/<patch-name>`: Urgent patches applied directly to `main` and back-ported to `develop`.

---

## 🛡️ Security Architecture

1. **Password Security**: Strong salted Bcrypt password hashing (`rounds=12`).
2. **Access Control**: Strict role checking dependencies (`get_current_student`, `get_current_faculty`). Students cannot access faculty endpoints or other students' private submissions.
3. **File Ingestion Safety**:
   - Extension whitelist validation (`.pdf`, `.docx`, `.zip`, etc.)
   - Sanitization of original filenames to prevent path traversal
   - Unique UUID prefixing
   - Chunked streaming upload validation enforcing the 25MB threshold
4. **Protected File Downloads**: Every file download is verified through backend authorization logic ensuring only instructors and authorized submitters can download files.

