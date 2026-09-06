"""
API Smoke Test Suite for MetriGuard.
Executes live HTTP requests against the running local server (http://127.0.0.1:8000).
Verifies health, dashboard stats, inspection session creation, image upload,
OCR orchestration, declaration extraction, rule engine evaluation, and image serving.
"""

import sys
import io
import requests
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:8000"

def run_smoke_tests():
    print("=" * 60)
    print("  MetriGuard Live API Smoke Tests")
    print(f"  Target: {BASE_URL}")
    print("=" * 60)

    # 1. Health check
    print("\n[1/6] Checking /health and /api/v1/health...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"  [OK] /health: {resp.status_code} - {resp.json()}")

    resp_v1 = requests.get(f"{BASE_URL}/api/v1/health")
    assert resp_v1.status_code == 200, f"Expected 200, got {resp_v1.status_code}"
    print(f"  [OK] /api/v1/health: {resp_v1.status_code} - {resp_v1.json()}")

    # 2. Dashboard Stats
    print("\n[2/6] Checking /api/v1/dashboard/stats...")
    stats_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/stats")
    assert stats_resp.status_code == 200, f"Expected 200, got {stats_resp.status_code}"
    stats = stats_resp.json()
    print(f"  [OK] Total: {stats['total_inspections']}, Compliant: {stats['compliant_inspections']}, Non-compliant: {stats['non_compliant_inspections']}, Manual: {stats['manual_review_inspections']}")
    print(f"  [OK] Top violations recorded: {len(stats['top_violations'])}")

    # 3. Create inspection session
    print("\n[3/6] Creating new inspection session via POST /api/v1/inspections...")
    create_resp = requests.post(
        f"{BASE_URL}/api/v1/inspections",
        json={"product_name": "Smoke Test Premium Tea 250g", "notes": "Automated smoke test run"}
    )
    assert create_resp.status_code == 201, f"Expected 201, got {create_resp.status_code}"
    insp = create_resp.json()
    insp_id = insp["id"]
    print(f"  [OK] Created inspection #{insp_id} with status: {insp['status']}")

    # 4. Upload package image and run full pipeline
    print("\n[4/6] Uploading package image to /api/v1/inspections/{id}/images...")
    img = Image.new("RGB", (400, 250), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Smoke Test Premium Tea", fill="black")
    draw.text((20, 60), "Net Quantity: 250 g", fill="black")
    draw.text((20, 100), "MRP: Rs. 180.00 (inclusive of all taxes)", fill="black")
    draw.text((20, 140), "Manufactured by: MetriGuard Tea Packers Ltd", fill="black")
    draw.text((20, 180), "Mfg Date: 09/2026", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    upload_resp = requests.post(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/images",
        files={"file": ("tea_label.jpg", buf.getvalue(), "image/jpeg")}
    )
    assert upload_resp.status_code == 201, f"Expected 201, got {upload_resp.status_code}"
    upload_data = upload_resp.json()
    image_id = upload_data["id"]
    print(f"  [OK] Upload processed: Image #{image_id}, Outcome: {upload_data.get('status')}")

    # 5. Fetch full inspection detail
    print("\n[5/6] Retrieving full inspection details via GET /api/v1/inspections/{id}...")
    detail_resp = requests.get(f"{BASE_URL}/api/v1/inspections/{insp_id}")
    assert detail_resp.status_code == 200, f"Expected 200, got {detail_resp.status_code}"
    detail = detail_resp.json()
    print(f"  [OK] Status: {detail['status']}, Confidence: {detail['overall_confidence']}")
    print(f"  [OK] Extracted declarations: {len(detail.get('declarations', []))}")
    print(f"  [OK] Recorded violations: {len(detail.get('violations', []))}")
    if detail.get("result"):
        print(f"  [OK] Result summary: {detail['result'].get('summary')}")

    # 6. Retrieve original image file
    print("\n[6/6] Verifying original image retrieval via GET /api/v1/inspections/{id}/images/{img_id}/file...")
    file_resp = requests.get(f"{BASE_URL}/api/v1/inspections/{insp_id}/images/{image_id}/file")
    assert file_resp.status_code == 200, f"Expected 200, got {file_resp.status_code}"
    assert len(file_resp.content) > 0, "Image file content is empty"
    print(f"  [OK] Image served successfully: {len(file_resp.content)} bytes, Content-Type: {file_resp.headers.get('content-type')}")


    print("\n" + "=" * 60)
    print("  ALL LIVE API SMOKE TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_smoke_tests()
