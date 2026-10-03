# MetriGuard
### AI-Assisted Legal Metrology Compliance Inspection Platform

MetriGuard is an AI-assisted inspection platform designed to help identify declaration-related compliance issues on packaged commodities under the **Legal Metrology (Packaged Commodities) Rules, 2011**. The system accepts a package image, extracts visible declarations using OCR and computer vision, evaluates the extracted information against a deterministic rule engine, and presents an explainable inspection result with supporting evidence.

> **Prototype notice:** MetriGuard is a decision-support prototype. It may produce OCR or interpretation errors and must not be treated as legal certification. Cases with incomplete, ambiguous, or insufficient evidence should be verified manually by a qualified inspector.

- **Prototype:** Prototype - MK I

---

## Overview

Manual inspection of packaged commodities can be repetitive, time-consuming, and difficult to standardize. Inspectors may need to verify multiple declarations, compare them against applicable rules, and document the basis for every finding.

MetriGuard aims to assist this process by combining:

- Package-image upload
- OCR-based declaration extraction
- Image preprocessing and perspective correction
- Structured declaration parsing
- Deterministic regulatory rule evaluation
- Evidence-backed findings
- Confidence-aware manual review
- Inspection history
- PDF reporting

The system is designed around the following principle:

> **AI extracts. Rules decide. Evidence supports.**

---

## Core Workflow

```text
Upload package image
       ↓
Image preprocessing
       ↓
OCR and declaration extraction
       ↓
Structured declaration parsing
       ↓
Deterministic rule evaluation
       ↓
Evidence and confidence analysis
       ↓
Inspection result
       ↓
Inspection history / PDF report
```

Each inspection contains one uploaded image and one associated inspection result. Starting another inspection creates a new inspection ID and does not overwrite the previous inspection.

---

## Inspection Outcomes

MetriGuard produces one of the following outcomes:

| Outcome | Meaning |
| --- | --- |
| `COMPLIANT` | The available evidence satisfies the implemented checks. |
| `NON_COMPLIANT` | The implemented rules identify one or more supported violations. |
| `MANUAL_REVIEW` | The evidence is incomplete, ambiguous, or insufficient for a reliable automated decision. |
| `FAILED` | The inspection process could not be completed because of a technical or input-processing failure. |

A technical failure is not treated as non-compliance. Similarly, an unreadable declaration is not automatically treated as a missing declaration.

---

## Current Capabilities

Depending on the current implementation, MetriGuard supports:

- Package image upload
- Local OCR processing
- Image preprocessing using OpenCV
- Structured extraction of package declarations
- Declaration parsing across the supported declaration types
- Deterministic compliance checks
- Confidence-aware inspection results
- Evidence and bounding-box display
- Inspection persistence
- Inspection history
- Local SQLite storage
- PDF inspection reports

Only the features implemented in the current codebase should be considered available in Prototype - MK I.

---

## Technology Stack

### Frontend
- React
- TypeScript
- Vite
- CSS-based responsive interface

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- SQLite for local development

### AI and Computer Vision
- PaddleOCR
- OpenCV
- Image preprocessing
- Structured declaration extraction

### Testing
- Pytest
- Vitest
- ESLint
- TypeScript build checks
- API smoke tests

---

## Project Structure

```text
metriguard/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── smoke_test.py
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── scripts/
│   ├── clean-dir.ps1
│   ├── start.ps1
│   └── verify-setup.ps1
├── README.md
├── CHANGELOG.md
├── LICENSE
└── SECURITY.md
```

The exact structure may change as the project evolves.

---

## Prerequisites

The current local development setup is intended for:

- Windows 10 or Windows 11, x64
- Python 3.11 or 3.12
- Node.js 18 or later
- npm
- PowerShell 5.1 or later
- Git

Verify the installations:

```powershell
python --version
node --version
npm --version
git --version
```

---

## Installation

### 1. Clone the repository

```powershell
git clone <REPOSITORY_URL>
cd <REPOSITORY_DIRECTORY>
```

Replace `<REPOSITORY_URL>` and `<REPOSITORY_DIRECTORY>` with the actual repository details.

### 2. Set up the backend

```powershell
cd backend
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

The application provides local development defaults. If you need to override them, create a `.env` file from the example:

```powershell
copy .env.example .env
```

Example configuration:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/metriguard.db
STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=10
CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]
HOST=127.0.0.1
PORT=8000
USE_MOCK_EXTRACTOR=false
```

Do not commit `.env` files containing local secrets or private configuration.

### 4. Apply database migrations

From the `backend` directory, with the virtual environment activated:

```powershell
alembic upgrade head
```

Check the current migration:

```powershell
alembic current
```

The expected migration revision may change as the schema evolves.

### 5. Set up the frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
```

The frontend defaults to the local backend at `http://127.0.0.1:8000`. If required, configure the API URL in `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## Running the Application

### Option A: One-click launcher

From the repository root:

```powershell
.\scripts\start.ps1
```

The launcher is intended to:
1. Check the local environment
2. Initialize required directories
3. Apply database migrations
4. Start the backend
5. Start the frontend

The application should then be available at:

| Service | URL |
| --- | --- |
| Frontend | [http://localhost:5173](http://localhost:5173) |
| Backend API | [http://127.0.0.1:8000](http://127.0.0.1:8000) |
| Swagger documentation | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) |
| Health endpoint | [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) |

### Option B: Manual startup

**Terminal 1 — Backend**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend**
```powershell
cd frontend
npm run dev
```

Open the frontend URL shown by Vite.

---

## Testing

Run the tests before creating a release or demonstrating the application.

### Setup verification

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-setup.ps1
```

### Backend tests

```powershell
cd backend
.\.venv\Scripts\pytest tests -q
```

### API smoke tests

With the backend running:

```powershell
backend\.venv\Scripts\python backend\smoke_test.py
```

The smoke tests should verify the main API workflow, including:
- Health check
- Image upload
- OCR extraction
- Rule evaluation
- Inspection retrieval
- Original image retrieval

### Frontend tests

```powershell
cd frontend
npm test -- --run
```

### Linting

```powershell
npm run lint
```

### Production build

```powershell
npm run build
```

A release should not be created solely because the happy-path demo works. The complete inspection lifecycle should also be tested.

---

## Recommended Manual Test Cases

Before a demonstration, test the following:

1. Select an image without starting an inspection
2. Cancel before upload
3. Start an inspection
4. Complete an inspection
5. Upload another image
6. Confirm that a new inspection ID is created
7. Confirm that the previous result does not appear in the new inspection
8. Confirm that both inspections remain in history
9. Upload an invalid file
10. Upload a very large image
11. Upload a blurry image
12. Upload an image with glare
13. Upload a rotated package image
14. Upload a non-package image
15. Test a case with missing or unreadable declarations
16. Test a case that should require manual review
17. Generate a report from a completed inspection

---

## Important Design Principles

### AI is not the final legal authority
OCR and computer vision are used to extract information from package images. The compliance decision is made by a deterministic rule engine using structured data and explicitly defined rules.

### Uncertainty must be visible
If the image is unclear or the extracted information cannot be verified, the system should return `MANUAL_REVIEW`. It should not invent declarations or convert uncertainty into a confident violation.

### Evidence must support findings
Where possible, each finding should contain:
- The extracted field
- The relevant image region
- The applicable rule ID
- The rule version
- An explanation
- Confidence or uncertainty information

### The system has limited regulatory scope
MetriGuard does not claim to cover every Legal Metrology requirement or every product category. The result represents an evaluation against the rules implemented in the current prototype and the evidence available in the uploaded image.

---

## PDF Reporting

MetriGuard can generate a report from a completed inspection. The report is generated from the saved inspection result. It does not rerun OCR or the rule engine.

A report may include:
- Inspection ID
- Inspection date and time
- Original uploaded image
- Extracted declarations
- Compliance outcome
- Findings and explanations
- Rule IDs and rule versions
- Evidence regions
- Confidence or manual-review notes
- Report generation timestamp
- Prototype disclaimer

The report is an inspection-support document and is not a legally binding certificate.

---

## Resetting Local Development Data

The cleanup script is intended to remove local development artifacts such as:
- Temporary uploads
- Generated files
- Cache files
- Local build outputs
- Local development database files

Before running the cleanup script:
1. Stop the frontend and backend.
2. Confirm that you do not need the local inspection history.
3. Run a dry run first.

From the repository root:

```powershell
.\scripts\clean-dir.ps1 -WhatIf
```

Run the interactive cleanup:

```powershell
.\scripts\clean-dir.ps1
```

Run without confirmation:

```powershell
.\scripts\clean-dir.ps1 -Force
```

After cleanup, recreate the database schema:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

Then restart the application:

```powershell
cd ..
.\scripts\start.ps1
```

The cleanup script is designed to only target disposable cache, build, temporary upload, and database files, preserving source code, configuration templates, migrations, and tracked project files.

---

## Troubleshooting

### PowerShell execution policy error
Run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
This changes the policy only for the current PowerShell session.

### Alembic cannot find the migration directory
Run Alembic from the backend directory:
```powershell
cd backend
.\.venv\Scripts\alembic upgrade head
```

### PaddleOCR or oneDNN error on Windows
MetriGuard disables the problematic CPU oneDNN path through its OCR provider configuration.

If the issue persists:
1. Confirm that the virtual environment is active.
2. Reinstall the backend dependencies.
3. Check the OCR provider logs.
4. Confirm that the installed PaddlePaddle and PaddleOCR versions are compatible.

### Unicode encoding error
If the Windows console cannot display certain characters:
```powershell
$env:PYTHONIOENCODING="utf-8"
```
Then rerun the command.

### Frontend cannot connect to the backend
Check that:
- The backend is running on port 8000.
- The frontend is running on port 5173.
- `VITE_API_URL` points to the correct backend URL.
- The backend CORS configuration includes the frontend origin.
- No other process is occupying the required ports.

---

## Limitations

The current prototype may be affected by:
- Blurry or low-resolution images
- Glare and reflections
- Curved or distorted packaging
- Small text
- Complex label layouts
- Mixed-language text
- Incorrect OCR extraction
- Ambiguous declaration applicability
- Lack of physical scale calibration
- Incomplete regulatory coverage

Pixel measurements alone cannot reliably prove physical font size in millimetres. Such checks require suitable calibration or a known reference scale. If calibration is unavailable, the case should be sent for manual review.

---

## Security and Privacy

MetriGuard is currently intended for local development and controlled prototype demonstrations. Do not upload confidential or sensitive product information unless the deployment has been configured for appropriate security and data handling.

Before production use, the system would require:
- Authentication and authorization
- Secure image storage
- Access controls
- Data retention and deletion policies
- HTTPS
- Input validation
- Rate limiting
- Audit logging
- Production database configuration
- Security testing

---

## Project Documentation

Additional documentation is available in the `docs/` directory:

- `ARCHITECTURE.md` — system architecture and component responsibilities
- `REQUIREMENTS.md` — functional and non-functional requirements
- `REGULATORY_RULES.md` — implemented rule definitions and versions
- `IMPLEMENTATION_STATUS.md` — implemented, partial, and planned features
- `API.md` — API endpoints and request/response formats
- `TESTING.md` — testing strategy and test coverage
- `DEPLOYMENT.md` — deployment instructions
- `LIMITATIONS.md` — known limitations and risks
- `DEMO_GUIDE.md` — recommended demonstration workflow

---

## Development Status

MetriGuard is currently an experimental prototype. The project is being developed incrementally, with emphasis on:
- Reliable inspection lifecycle handling
- Explainable findings
- Deterministic rule evaluation
- Safe handling of uncertainty
- Reproducible results
- Evidence traceability

---

## License

See [LICENSE](LICENSE).

---

## Disclaimer

MetriGuard is an AI-assisted preliminary inspection system. It is not a substitute for a qualified inspector, legal advice, official certification, or enforcement action. All results must be independently verified before being used for regulatory, commercial, or legal decisions.