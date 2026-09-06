"""
MetriGuard - Native Windows Backend Verification Script
Verifies:
1. Python version (>= 3.11)
2. Required packages (fastapi, uvicorn, sqlalchemy, alembic, pydantic, pydantic_settings, multipart, pytest, httpx)
3. Database connection (SQLite)
4. Writable storage directories (data/, storage/, storage/uploads/, storage/reports/)
5. Health endpoint availability (GET /health -> {"status": "ok"})
"""

import sys
import os
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def print_check(name: str, passed: bool, detail: str = ""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f" {status} {name}")
    if detail:
        print(f"        {detail}")


def main():
    print("=" * 60)
    print("  MetriGuard Native Windows Backend Verification")
    print("=" * 60)
    print()

    all_passed = True

    # 1. Check Python version (>= 3.11)
    major, minor = sys.version_info.major, sys.version_info.minor
    py_ver_str = f"{major}.{minor}.{sys.version_info.micro}"
    py_ok = (major == 3 and minor >= 11) or major > 3
    if not py_ok:
        all_passed = False
    print_check(
        "Python Version (>= 3.11)",
        py_ok,
        f"Detected Python {py_ver_str} at {sys.executable}"
    )

    # 2. Check Required Packages
    required_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("alembic", "alembic"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("multipart", "python-multipart"),
        ("pytest", "pytest"),
        ("httpx", "httpx"),
    ]

    missing_pkgs = []
    found_pkgs = []
    for import_name, pkg_name in required_packages:
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", "installed")
            found_pkgs.append(f"{pkg_name} ({ver})")
        except ImportError:
            missing_pkgs.append(pkg_name)

    pkgs_ok = len(missing_pkgs) == 0
    if not pkgs_ok:
        all_passed = False
        print_check("Required Packages", False, f"Missing: {', '.join(missing_pkgs)}")
    else:
        print_check("Required Packages", True, f"All {len(found_pkgs)} skeleton dependencies installed.")

    # 3. Check Database Connection (SQLite)
    db_ok = False
    db_msg = ""
    try:
        from sqlalchemy import text
        from app.db.database import engine
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                db_ok = True
                db_msg = f"Connected successfully: {engine.url}"
            else:
                db_msg = f"Unexpected query result: {result}"
    except Exception as e:
        db_msg = f"Database connection error: {e}"

    if not db_ok:
        all_passed = False
    print_check("Database Connection (SQLite)", db_ok, db_msg)

    # 4. Check Writable Storage Directories
    from app.core.config import settings, ensure_directories
    ensure_directories()

    storage_root = settings.get_resolved_storage_path()
    data_root = BACKEND_DIR / "data"
    dirs_to_check = [
        ("data", data_root),
        ("storage", storage_root),
        ("storage/uploads", storage_root / "uploads"),
        ("storage/reports", storage_root / "reports"),
    ]

    storage_ok = True
    storage_msgs = []
    for dir_name, dir_path in dirs_to_check:
        if not dir_path.is_dir():
            storage_ok = False
            storage_msgs.append(f"{dir_name} does not exist")
            continue

        probe_file = dir_path / f".write_probe_{uuid.uuid4().hex[:8]}.tmp"
        try:
            probe_file.write_text("probe", encoding="utf-8")
            probe_file.unlink()
        except Exception as e:
            storage_ok = False
            storage_msgs.append(f"{dir_name} not writable: {e}")

    if not storage_ok:
        all_passed = False
        print_check("Writable Storage Directories", False, "; ".join(storage_msgs))
    else:
        print_check(
            "Writable Storage Directories",
            True,
            f"Verified data/, storage/, storage/uploads/, and storage/reports/ at {storage_root}"
        )

    # 5. Check Health Endpoint Availability
    health_ok = False
    health_msg = ""
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            if data == {"status": "ok"}:
                health_ok = True
                health_msg = 'GET /health returned HTTP 200 with {"status": "ok"}'
            else:
                health_msg = f"HTTP 200 but unexpected response: {data}"
        else:
            health_msg = f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        health_msg = f"Error querying health endpoint: {e}"

    if not health_ok:
        all_passed = False
    print_check("Health Endpoint Availability", health_ok, health_msg)

    print()
    print("=" * 60)
    if all_passed:
        print("  ALL CHECKS PASSED: Backend is ready for native Windows.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("  SOME CHECKS FAILED: Please review issues above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
