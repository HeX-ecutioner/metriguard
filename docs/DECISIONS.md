# MetriGuard Architectural Decision Records (ADRs)

This document records the key technical and architectural design decisions made for **MetriGuard** (developed by team **AlgoForge** for problem statement **SIH26034**).

## Decision 1: Web Application Architecture (Decoupled React Frontend + FastAPI Backend)

### Status
Accepted

### Context
The SIH26034 problem statement requires an accessible inspection interface for operators to upload package images, review extracted declarations, and inspect compliance findings across multiple devices.

### Decision
Adopt a decoupled web application architecture consisting of a React 18 single-page application (built with Vite & TypeScript) and a FastAPI backend service communicating over RESTful HTTP APIs.

### Rationale
- **Separation of Concerns:** Allows independent development, testing, and deployment of the frontend user interface and backend processing pipeline.
- **FastAPI Performance:** Python ASGI framework providing automatic OpenAPI schema generation, fast asynchronous handling, and typed Pydantic validation.
- **Vite Developer Experience:** Rapid frontend iteration and optimized static production bundling.

### Consequences
- **Benefits:** Clean API boundary, easy to test via Pytest and Vitest, cross-platform browser availability.
- **Trade-offs:** Requires running two services (backend port 8000 and frontend port 5173) or serving frontend static assets via reverse proxy.

### Alternatives Considered
- Desktop native application (Electron / PyQt): Rejected due to higher deployment complexity and installation overhead for operators.

## Decision 2: Decoupled OCR Extraction from Deterministic Rule Evaluation

### Status
Accepted

### Context
Computer vision OCR algorithms extract raw text and coordinates from images, whereas legal compliance requires evaluating structured business logic. Mixing OCR logic directly with legal rules leads to fragile, unmaintainable code.

### Decision
Strictly separate the OCR and text extraction pipeline (`backend/app/services/ocr/` and `backend/app/services/extraction/`) from the compliance rule engine (`backend/app/services/rules/`).

### Rationale
- **Modularity:** OCR providers can be swapped (e.g. PaddleOCR to Tesseract or Mock provider) without modifying legal rule logic.
- **Testability:** Rule evaluation can be tested deterministically with mock declaration facts without invoking heavy OCR vision models.

### Consequences
- **Benefits:** High test reliability, clear pipeline stage boundaries, independent module evolution.
- **Trade-offs:** Requires an intermediate data transfer model (`PackageFacts` and `ExtractedDeclaration`) between pipeline stages.

## Decision 3: Deterministic Rule Engine over LLM Legal Generation

### Status
Accepted

### Context
Generative AI and Large Language Models (LLMs) are prone to non-deterministic outputs, hallucinations, and unpredictable reasoning, which is unacceptable for statutory compliance verification under Legal Metrology rules.

### Decision
Codify legal rules as 100% deterministic Python modules (`backend/app/services/rules/lmr_2011/`) operating on versioned rule logic. LLM models (if used) are restricted solely to optional extraction assistance (`ai_extractor.py`).

### Rationale
- **Auditability & Explainability:** Every compliance pass or fail determination is 100% reproducible and directly traceable to specific statutory rule criteria.
- **Zero Hallucination Guarantee:** The rule engine never invents facts or generates non-existent legal violations.

### Consequences
- **Benefits:** Reliable, audit-proof compliance decisions and fast rule execution speed.
- **Trade-offs:** Adding new legal rules requires authoring Python rule classes rather than prompting an LLM.

### Alternatives Considered
- Direct LLM Prompt-based Compliance Decisioning: Rejected due to non-determinism, hallucination risk, and lack of statutory auditability.

## Decision 4: Safe Routing of Missing or Low-Confidence Cases to MANUAL_REVIEW

### Status
Accepted

### Context
OCR extraction on packaging labels can fail due to reflections, unusual typography, or missing mandatory declarations. Forcing an automated `COMPLIANT` or `NON_COMPLIANT` judgment on ambiguous evidence causes false enforcement notices.

### Decision
Enforce a safe routing mechanism where any missing mandatory declaration or extraction confidence score below `0.60` (rule-level) / `0.70` (overall) automatically assigns the inspection status to `MANUAL_REVIEW`.

### Rationale
- **Human-in-the-Loop Philosophy:** Empowers human inspectors to make final decisions when machine vision evidence is uncertain.
- **Safety First:** Prevents false positive non-compliance penalties and false negative compliance approvals.

### Consequences
- **Benefits:** High trust, zero false compliance claims, and safe operator workflow.
- **Trade-offs:** Requires human operator review for low-quality or incomplete packaging photos.

## Decision 5: Single-Image Inspection Lifecycle Contract (1 Image per Session)

### Status
Accepted

### Context
Allowing multiple image uploads within an active inspection session created desynchronization bugs where extractions from image #2 mixed with image #1, corrupting database records and UI reports.

### Decision
Enforce a strict 1:1 single-image inspection lifecycle contract across database constraints (`uq_package_images_inspection_id`), backend orchestrator, and frontend state machine.

### Rationale
- **Data Integrity:** Guarantees one inspection session contains exactly one package image, one OCR result, one declaration set, and one compliance report.
- **Deterministic State Machine:** Clean frontend workflow (`IDLE` -> `IMAGE_SELECTED` -> `PROCESSING` -> `COMPLETED` -> `RESET`).

### Consequences
- **Benefits:** Eliminates result contamination bugs and simplifies inspection history audit trails.
- **Trade-offs:** Scanning front and back packaging faces requires creating two separate inspection sessions.

## Decision 6: Evidence-Linked Findings with Bounding Box Coordinates

### Status
Accepted

### Context
Inspectors need visual proof of where a declaration was detected on a package label to verify automated findings.

### Decision
Store bounding box coordinates `[x_min, y_min, x_max, y_max]` for every extracted declaration and link rule evaluation findings to exact evidence text snippets and image overlays.

### Rationale
- **Verifiable AI:** Inspectors can click any extracted value or violation card to highlight the exact visual region on the packaging photo in the UI viewer.

### Consequences
- **Benefits:** Complete explainability and rapid visual verification by operators.
- **Trade-offs:** Requires storing and transmitting bounding box JSON data in API responses.

## Decision 7: Embedded Relational Storage via SQLite & Alembic Migrations

### Status
Accepted

### Context
The prototype requires persistent local storage for inspection sessions, declarations, and violations without forcing complex external database installation for demonstration environments.

### Decision
Use SQLite (`backend/data/metriguard.db`) with SQLAlchemy ORM and Alembic versioned schema migrations (`alembic/versions/`).

### Rationale
- **Zero Configuration:** Embedded SQLite requires no external database server setup for local execution.
- **Production Migration Path:** SQLAlchemy ORM allows migrating to PostgreSQL by changing `DATABASE_URL` in `.env`.

### Consequences
- **Benefits:** Simple setup, single-file database backup, instant prototype deployment.
- **Trade-offs:** SQLite is limited to single-node file locking and cannot scale horizontally across multi-server clusters.

## Decision 8: Native Host Engine Execution over Heavy Microservices Architecture

### Status
Accepted

### Context
Overengineering an MVP prototype with Kubernetes, Kafka, Redis, and multi-container microservices introduces deployment friction and setup failures during demonstration.

### Decision
Deploy as a monolithic FastAPI application with native local background launchers ([`start.ps1`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/start.ps1)) running directly on host Python virtual environment.

### Rationale
- **Simplicity & Reliability:** Minimal moving parts; easy to launch and verify via single script.
- **Resource Efficiency:** Runs efficiently on standard laptops without Docker container overhead.

### Consequences
- **Benefits:** Fast startup, zero container dependency issues on host machines.
- **Trade-offs:** Heavy CPU tasks (e.g. OCR) run synchronously within backend worker threads.

## Decision 9: Native PaddleOCR Provider with Deterministic Mock Fallback

### Status
Accepted

### Context
OCR text detection must support real package image text extraction while maintaining reliable headless execution for automated unit testing and CI environments.

### Decision
Implement `PaddleOCRProvider` for native execution, paired with `MockOCRProvider` via a unified `OCRProvider` factory interface ([`factory.py`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/app/services/ocr/factory.py)).

### Rationale
- **Native Accuracy:** PaddleOCR (PP-OCRv6) provides accurate multilingual line text detection.
- **Headless Test Reliability:** MockOCRProvider allows running Pytest suites offline in milliseconds without loading heavy neural network weights.

### Consequences
- **Benefits:** Dual-mode execution ensures fast automated testing and accurate live OCR inference.
- **Trade-offs:** PaddleOCR requires C++ CPU runtime libraries and initial model weight downloads.

## Decision 10: Positioning as an AI-Assisted Decision-Support Prototype

### Status
Accepted

### Context
Claiming that an AI prototype provides legally certified enforcement action exposes the project to legal liability and regulatory non-compliance.

### Decision
Explicitly position MetriGuard in documentation, UI headers, and API disclaimers as an **AI-assisted decision-support prototype** for legal metrology inspection.

### Rationale
- **Regulatory Realism:** Acknowledges that final legal compliance authority rests with certified human inspectors.
- **Ethical AI Alignment:** Maintains human agency and accountability in automated regulatory workflows.

### Consequences
- **Benefits:** Protects project integrity, sets realistic expectations for hackathon judges, and aligns with ethical AI principles.
- **Trade-offs:** None.
