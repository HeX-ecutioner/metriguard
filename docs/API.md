# MetriGuard REST API Documentation

## 1. API Overview
The **MetriGuard** REST API provides endpoints for packaged-commodity image uploads, OCR text detection, declaration parsing, deterministic legal metrology rule evaluation, inspection session retrieval, and aggregated metrics.

The API is implemented using **FastAPI** (Python 3.10+) and communicates strictly via JSON payloads and multipart/form-data image uploads.

## 2. Base URL & Versioning
- **Local Base URL:** `http://127.0.0.1:8000`
- **API Version Prefix:** `/api/v1`
- **Interactive OpenAPI Documentation:** Available at `http://127.0.0.1:8000/docs` (Swagger UI) and `http://127.0.0.1:8000/redoc`.

## 3. Authentication & CORS
- **Authentication:** Unauthenticated. Prototype endpoints do not require API keys or JWT bearer tokens.
- **CORS Configuration:** Managed via `CORSMiddleware` reading allowed origin hosts from `CORS_ORIGINS` (defaults to `http://localhost:5173`).

## 4. Endpoint Specifications

### 4.1 Health Check Endpoints

#### `GET /health`
- **Purpose:** Simple Liveness probe.
- **Authentication:** None.
- **Request Format:** None.
- **Response Status:** `200 OK`
- **Response Example:**
  ```json
  {
    "status": "ok"
  }
  ```

#### `GET /health/detail`
- **Purpose:** Diagnostic health check verifying database connection, storage directory, and OCR mode.
- **Authentication:** None.
- **Response Status:** `200 OK`
- **Response Example:**
  ```json
  {
    "status": "healthy",
    "database": {
      "status": "connected",
      "details": "sqlite:///c:/.../backend/data/metriguard.db"
    },
    "storage": {
      "status": "available",
      "type": "local",
      "path": "c:/.../backend/storage"
    },
    "ai_extractor": {
      "mode": "ocr"
    },
    "version": "1.0.0"
  }
  ```

### 4.2 Inspection Management Endpoints

#### `POST /api/v1/inspections`
- **Purpose:** Creates a new empty inspection session in the database.
- **Authentication:** None.
- **Request Format:** `application/json` (optional body).
- **Optional Request Fields:**
  - `product_name` (string, optional): Product name label.
  - `notes` (string, optional): Inspector notes.
- **Response Status:** `201 Created`
- **Example Request:**
  ```json
  {
    "product_name": "Standard Wheat Flour 5kg",
    "notes": "Retail store sample"
  }
  ```
- **Example Response:**
  ```json
  {
    "id": 12,
    "status": "CREATED",
    "product_name": "Standard Wheat Flour 5kg",
    "overall_confidence": null,
    "notes": "Retail store sample",
    "created_at": "2026-09-06T22:00:00Z",
    "updated_at": "2026-09-06T22:00:00Z",
    "images": []
  }
  ```

#### `POST /api/v1/inspections/{inspection_id}/images`
- **Purpose:** Uploads a package image to an existing inspection session and executes the full 5-stage pipeline (Validation -> Storage -> OCR -> Extraction -> Rule Evaluation -> DB Persistence).
- **Authentication:** None.
- **Path Parameters:**
  - `inspection_id` (integer, required): Target inspection session ID.
- **Request Format:** `multipart/form-data`
- **Required Form Fields:**
  - `file` (binary, required): Image file (JPEG, PNG, WEBP $\le$ 10 MB).
- **Response Status:** `201 Created` (Success), `400 Bad Request` (Invalid file), `409 Conflict` (Inspection session already has an uploaded image).
- **Example Response (`PackageImageResponse`):**
  ```json
  {
    "id": 15,
    "inspection_id": 12,
    "file_path": "a1b2c3d4_package.jpg",
    "original_filename": "package.jpg",
    "mime_type": "image/jpeg",
    "file_size": 245120,
    "width": 1920,
    "height": 1080,
    "created_at": "2026-09-06T22:00:05Z"
  }
  ```

#### `GET /api/v1/inspections/{inspection_id}`
- **Purpose:** Retrieves complete inspection details, including attached images, parsed declarations, rule violations, and outcome.
- **Authentication:** None.
- **Path Parameters:** `inspection_id` (integer).
- **Response Status:** `200 OK`, `404 Not Found`.
- **Example Response (`InspectionDetailResponse`):**
  ```json
  {
    "id": 12,
    "status": "COMPLIANT",
    "product_name": "Standard Wheat Flour 5kg",
    "overall_confidence": 0.92,
    "notes": "Retail store sample",
    "created_at": "2026-09-06T22:00:00Z",
    "updated_at": "2026-09-06T22:00:05Z",
    "images": [
      {
        "id": 15,
        "inspection_id": 12,
        "file_path": "a1b2c3d4_package.jpg",
        "original_filename": "package.jpg",
        "mime_type": "image/jpeg",
        "file_size": 245120,
        "width": 1920,
        "height": 1080,
        "created_at": "2026-09-06T22:00:05Z"
      }
    ]
  }
  ```

#### `GET /api/v1/inspections`
- **Purpose:** Retrieves paginated inspection sessions with status and search filtering.
- **Authentication:** None.
- **Query Parameters:**
  - `skip` (integer, default `0`): Pagination offset.
  - `limit` (integer, default `50`): Maximum records to return.
  - `status` (string, optional): Filter by status (`COMPLIANT`, `NON_COMPLIANT`, `MANUAL_REVIEW`, `FAILED`).
  - `search` (string, optional): Substring search across product names and notes.
- **Response Status:** `200 OK`

#### `GET /api/v1/inspections/{inspection_id}/images/{image_id}/file`
- **Purpose:** Serves the raw uploaded package image binary file for image viewing.
- **Authentication:** None.
- **Path Parameters:** `inspection_id` (integer), `image_id` (integer).
- **Response Status:** `200 OK` (Returns file stream with appropriate `Content-Type` header), `404 Not Found`.

### 4.3 Dashboard Endpoints

#### `GET /api/v1/dashboard/stats`
- **Purpose:** Aggregates real-time metrics for dashboard cards and top violation charts.
- **Authentication:** None.
- **Response Status:** `200 OK`
- **Example Response:**
  ```json
  {
    "total_inspections": 42,
    "compliant_inspections": 28,
    "non_compliant_inspections": 10,
    "manual_review_inspections": 4,
    "top_violations": [
      {
        "rule_id": "LMR-2011-R06-1-E",
        "title": "Maximum Retail Price (MRP) Declaration",
        "severity": "CRITICAL",
        "count": 6
      }
    ],
    "recent_inspections": []
  }
  ```

### 4.4 Decoupled OCR & Extraction Endpoints

#### `POST /api/v1/ocr/process`
- **Purpose:** Direct standalone OCR text recognition on raw uploaded image file (decoupled from legal compliance).
- **Request Format:** `multipart/form-data` (`file` parameter).
- **Response Status:** `200 OK`, `400 Bad Request`, `504 Gateway Timeout`.

#### `POST /api/v1/extract/declarations`
- **Purpose:** Parses mandatory Legal Metrology declarations directly from raw multiline OCR text or OCR items.
- **Request Format:** `application/json` (`DirectExtractionRequest`).

## 5. File-Upload Restrictions
- **Maximum File Size:** 10 MB (`MAX_UPLOAD_SIZE_MB`).
- **Allowed MIME Types:** `image/jpeg`, `image/png`, `image/webp`.
- **Allowed Extensions:** `.jpg`, `.jpeg`, `.png`, `.webp`.
- **Byte Validation:** `PIL.Image.open().verify()` must pass; fake or corrupt files trigger `400 Bad Request`.

## 6. Error Handling Format
All API error responses follow the standard FastAPI / RFC 7807 JSON error schema:

```json
{
  "detail": "Descriptive error message detailing why the request failed."
}
```

### Standard HTTP Status Codes:
- `200 OK` - Request succeeded.
- `201 Created` - Resource successfully created.
- `400 Bad Request` - Invalid input file format, corrupt image bytes, or missing required fields.
- `404 Not Found` - Requested inspection session or image ID does not exist.
- `409 Conflict` - Single-image lifecycle invariant violation (e.g. attempting to upload a 2nd image to an existing inspection).
- `500 Internal Server Error` - Unhandled system exception or processing error.

## 7. Example Frontend Client Code (TypeScript)

```ts
import { apiClient } from './api/client';

// 1. Create inspection session
const inspection = await apiClient.createInspection({ product_name: 'Sample Tea Packaging' });

// 2. Upload image and execute inspection pipeline
const uploadedImage = await apiClient.uploadInspectionImage(
  inspection.id,
  selectedFile,
  (percent) => console.log(`Progress: ${percent}%`)
);

// 3. Retrieve final inspection report
const report = await apiClient.getInspection(inspection.id);
console.log('Inspection Status:', report.status);
```