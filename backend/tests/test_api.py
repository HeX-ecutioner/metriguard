from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Metriguard API is running"}

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "storage" in data

def test_health_v1_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("healthy", "degraded")

def test_inspect_valid_image():
    response = client.post(
        "/api/v1/inspect",
        files={"file": ("sample.jpg", b"\xff\xd8\xff\xe0fakejpegdata", "image/jpeg")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("COMPLIANT", "NON_COMPLIANT", "MANUAL_REVIEW")
    assert isinstance(data["violations"], list)
    assert isinstance(data["extracted_texts"], list)
    assert isinstance(data["confidence_score"], (int, float))

def test_inspect_invalid_file_type():
    response = client.post(
        "/api/v1/inspect",
        files={"file": ("document.txt", b"plain text", "text/plain")}
    )
    assert response.status_code == 400
    assert "not an image" in response.json()["detail"].lower()

def test_inspect_empty_file():
    response = client.post(
        "/api/v1/inspect",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

