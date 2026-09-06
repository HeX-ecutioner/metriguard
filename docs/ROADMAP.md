# MetriGuard Project Roadmap

## 1. Overview & Core Engineering Principles
This roadmap outlines the past achievements, current priorities, pre-demonstration targets, post-demo improvements, and long-term proposals for **MetriGuard** (developed by team **AlgoForge** for **SIH26034**).

### Core Priorities:
1. **Zero AI Hallucination:** Maintain 100% deterministic rule evaluations linked to verifiable OCR text evidence.
2. **Explainable Findings:** Every compliance result must map to exact bounding box coordinates and raw text evidence.
3. **Safe Manual Review:** Low confidence or missing declarations must route safely to human inspectors (`MANUAL_REVIEW`).
4. **Engineering Rigor over Flashy Features:** Prioritize accuracy, test coverage, data integrity, and deployment stability over overengineered microservices.

## 2. Phase 0: Completed Foundation (Current Repository State)

### Core Pipeline & Architecture
- [x] Decoupled React 18 frontend (Vite, TypeScript, TailwindCSS) and FastAPI backend architecture.
- [x] Automated 5-stage inspection lifecycle: Validation -> Storage -> OCR -> Extraction -> Rule Evaluation -> Persistence.
- [x] Single-image inspection session lifecycle contract enforced via Alembic migration (`003_one_image_per_inspection`).
- [x] Local storage service with UUID filename key sanitization and `is_relative_to` path traversal protection.

### Optical Recognition & Rule Engine
- [x] Native PaddleOCR provider with automatic OpenCV preprocessing (grayscale, contrast adjustment, bilateral filtering).
- [x] Headless `MockOCRProvider` fallback for unit testing and offline environments.
- [x] Deterministic regex extraction across MRP, Net Quantity, Manufacture/Packing Date, Entity Name & Address, Consumer Care Details, and Unit Sale Price.
- [x] 6 codified prototype rules under Legal Metrology (Packaged Commodities) Rules, 2011 (`LMR-2011-R06-1-A`, `R06-1-C`, `R06-1-D`, `R06-1-E`, `R06-1-G`, `R06-11`).

### Quality, Verification, & Documentation
- [x] Comprehensive backend test suite (132 Pytest test cases covering rules, extraction, lifecycle, DB, and API).
- [x] Frontend test suite (11 Vitest component test cases).
- [x] Native Windows launch script ([`start.ps1`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/start.ps1)) and automated verification script ([`verify_setup.ps1`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/verify_setup.ps1)).
- [x] Comprehensive documentation suite (`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `REQUIREMENTS.md`, `REGULATORY_RULES.md`, `IMPLEMENTATION_STATUS.md`, `DEPLOYMENT.md`, `TESTING.md`, `LIMITATIONS.md`, `API.md`, `DEMO_GUIDE.md`, `DATA_AND_PRIVACY.md`, `DECISIONS.md`).

## 3. Phase 1: Current Priority (SIH Hackathon Preparation)

- [ ] **Benchmark Test Image Suite:** Prepare a benchmark folder of 4 real retail packaging images (Compliant, Non-Compliant, Manual Review, Invalid) for live judge demonstrations.
- [ ] **Demo Database Pre-seeding:** Run initial sample inspections prior to judge presentations to populate the Dashboard metrics and history table.
- [ ] **PaddleOCR Model Weight Pre-warming:** Execute one test upload prior to live presentation to cache PaddleOCR C++ model weights in memory.

## 4. Phase 2: Before SIH Demonstration (Final Polish)

- [ ] **Interactive Presentation Practice:** Practice the 5-minute demonstration script in [`docs/DEMO_GUIDE.md`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/docs/DEMO_GUIDE.md).
- [ ] **Backup Environment Verification:** Verify execution of standalone live API smoke test (`backend/smoke_test.py`) as backup presentation option.

## 5. Phase 3: Post-Demo Improvements (Production Hardening)

### Feature Extensions
- [ ] **Multi-Face Package Inspection Sessions (Proposed):** Support linking separate front, back, and side package photos into a single unified inspection record.
- [ ] **Expanded LMR 2011 Rule Coverage (Proposed):** Codify Schedule II standard package capacity rules (e.g. tea, biscuits, baby food) and E-commerce Rule 6(10) requirements.
- [ ] **Regional Language OCR Support (Proposed):** Extend OCR dictionaries and regex patterns to support regional Indian languages (Hindi, Tamil, Bengali).

### Infrastructure & Security
- [ ] **User Authentication & RBAC (Proposed):** Implement JWT bearer token authentication and inspector/admin role-based access control.
- [ ] **PostgreSQL Migration (Proposed):** Migrate database configuration from SQLite to PostgreSQL for concurrent multi-user write throughput.
- [ ] **Async Task Queue Architecture (Proposed):** Offload CPU-heavy PaddleOCR inference to Celery/Redis background worker queues.
- [ ] **Data Retention & Expiry TTL (Proposed):** Implement automated data purging for demonstration inspection records older than $N$ days.

## 6. Phase 4: Long-Term Possibilities (Future Research)

- [ ] **Fiducial Scale Reference Integration (Proposed):** Support millimeter reference rulers in photos to enable calibrated physical font height (Rule 7/9) and PDP surface area measurements.
- [ ] **Automated PII / Face Redaction (Proposed):** Automatically detect and blur human faces or extraneous personal text from uploaded packaging photos.
- [ ] **Mobile Field Inspection Web App (Proposed):** Optimize camera capture workflows for tablet and mobile browser viewports for field officers.