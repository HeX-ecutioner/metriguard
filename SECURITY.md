# Security Policy for MetriGuard

## 1. Scope of the Security Policy
This security policy applies to the **MetriGuard** repository codebase, including:
- FastAPI backend services (`/backend`)
- React frontend interface (`/frontend`)
- OCR processing and compliance analysis modules (`/backend/app/services`)
- Database models and file-storage operations (`/backend/app/storage.py`)

**Out of Scope:**
- Third-party OCR engines (e.g., Tesseract OCR system binary installations).
- External database drivers or operating system level dependencies.

## 2. Disclaimer: Prototype & Non-Legal Authority
> [!IMPORTANT]
> **MetriGuard is an AI-assisted packaged-commodity inspection prototype.**
> - It is designed for demonstration, educational, and testing purposes.
> - **It is not a legally certified compliance authority or enforcement system.**
> - Results produced by the system (OCR extractions, compliance findings, violation reports) must be independently validated by human operators.

## 3. How to Report a Vulnerability
Because this project is a demonstration prototype without a dedicated 24/7 Security Operations Center (SOC) or security email, vulnerabilities should be reported as follows:

- **Preferred Method:** Open a [Private Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-communicating-vulnerabilities/reporting-a-vulnerability) directly via the repository's **Security** tab on GitHub (if enabled by repository maintainers).
- **Alternative Method:** If private security advisories are not enabled, contact the repository maintainers directly via repository issue/discussion channels, marking the title clearly as `[SECURITY]` without disclosing actionable exploit details publicly.

*Note: Do not open public issues containing functional exploit code or zero-day vulnerability details before maintainers have had an opportunity to review.*

## 4. Required Report Information
When reporting a security vulnerability, please include:
1. **Description:** Clear summary of the vulnerability and its potential impact.
2. **Component:** Affected module or endpoint (e.g., `/api/v1/inspections`, `storage.py`, frontend component).
3. **Reproduction Steps:** Step-by-step instructions or minimal non-destructive proof-of-concept (PoC).
4. **Environment:** OS, Python version, Node.js version, and browser details used during testing.
5. **Mitigation Suggestion:** Any proposed fix or remediation strategy, if known.

## 5. Responsible Disclosure Expectations
- **Timely Review:** Maintainers will make reasonable efforts to review reported security issues promptly.
- **Coordination:** Reporters are asked to allow maintainers a reasonable window to patch confirmed issues before public disclosure.
- **No Bug Bounty:** This is an open-source prototype, AlgoForge does not offer a monetary bug bounty or financial reward program.

## 6. Supported Versions
Security updates and patches are applied only to the active development branch (`main`). Older commits or unmerged development branches are not actively maintained for security patches.

| Version / Branch | Supported | Notes |
| :--- | :--- | :--- |
| `main` (Latest) | Yes | Primary development branch receiving fixes |
| Historical Commits / Pre-release | No | Untrracked / unpatched |

## 7. Sensitive Information & Secret Management
### Guidelines:
- **Never Commit Secrets:** Passwords, API keys, JWT secrets, database credentials, or private configuration files must **never** be committed to Git.
- **Environment Variables:** All secrets and environment-specific settings are loaded dynamically via `pydantic-settings` from local `.env` files (see [`.env.example`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/.env.example)).
- **Git Ignore:** Ensure `backend/.env`, `*.pyc`, `data/*.db`, and `data/uploads/` remain strictly listed in `.gitignore`.

## 8. File-Upload Security Considerations
The application accepts package images for OCR and compliance inspection. Current file handling implements the following safeguards:
- **MIME & Format Validation:** Uploaded files are checked against allowed image MIME types (`image/jpeg`, `image/png`, `image/webp`) and verified via `PIL.Image.open().verify()` to prevent malicious payload execution or disguised file formats.
- **Size Limits:** File uploads are restricted to a maximum of 10 MB.
- **Path Traversal Prevention:** Uploaded files are stored with randomly generated UUID filename prefixes (`uuid4().hex`) and paths are validated via `is_relative_to()` to prevent directory traversal (`../`) attacks.
- **Storage Isolation:** Uploaded images are stored in a designated local directory (`backend/data/uploads`) separated from executable code binaries.

## 9. API & CORS Considerations
- **CORS Policy:** FastAPI is configured with `CORSMiddleware`. Allowed origins are specified via the `CORS_ORIGINS` environment variable (defaulting to `http://localhost:5173`).
- **Open API Access:** In the current prototype state, API endpoints do not require authentication or authorization tokens.

## 10. Privacy & Data Handling
### Warning on Uploaded Data
> [!WARNING]
> **Do NOT upload images containing personally identifiable information (PII), confidential business data, financial records, or sensitive personal media.**

- Uploaded package images are processed locally by the application backend and saved to the local server storage.
- Images uploaded during demonstration runs may be visible in inspection history lists.
- Avoid uploading images with clear faces, personal residential addresses, personal phone numbers, or non-public packaging metadata.

## 11. Dependency Management
- **Backend:** Managed using standard Python package management tools (`uv` or `pip`). Dependencies are listed in [`pyproject.toml`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/backend/pyproject.toml).
- **Frontend:** Managed using `npm`. Dependencies are tracked in [`package.json`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/package.json) and [`package-lock.json`](file:///c:/Users/Sagnik/Documents/GitHub repos/metriguard/frontend/package-lock.json).
- **Security Updates:** Run `npm audit` and keep Python dependencies updated regularly to mitigate known vulnerabilities in upstream packages.
