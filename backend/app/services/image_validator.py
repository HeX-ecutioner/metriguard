import io
from pathlib import Path
from typing import Tuple
from PIL import Image, UnidentifiedImageError

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageValidationError(Exception):
    """Custom exception raised when image validation fails."""
    def __init__(self, detail: str, error_code: str = "INVALID_IMAGE", status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code


class ValidatedImage:
    def __init__(self, mime_type: str, detected_format: str, width: int, height: int, file_size: int):
        self.mime_type = mime_type
        self.detected_format = detected_format
        self.width = width
        self.height = height
        self.file_size = file_size


def validate_and_decode_image(
    content: bytes,
    original_filename: str,
    content_type: str,
    max_size_mb: int = 10
) -> ValidatedImage:
    """
    Performs comprehensive validation on uploaded image bytes:
    1. Empty file detection
    2. File size limit
    3. File extension verification
    4. Declared MIME type verification
    5. Byte-level image decoding and integrity check with Pillow
    6. Image dimension bounds verification
    """
    file_size = len(content)

    # 1. Empty file validation
    if file_size == 0:
        raise ImageValidationError(
            detail="Uploaded file is empty.",
            error_code="EMPTY_FILE",
            status_code=400
        )

    # 2. File size limit validation
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        raise ImageValidationError(
            detail=f"File size of {file_size / (1024 * 1024):.2f}MB exceeds the maximum allowed limit of {max_size_mb}MB.",
            error_code="FILE_TOO_LARGE",
            status_code=413
        )

    # 3. File extension validation
    # Extract extension safely, ignoring any directory path components
    safe_name = Path(original_filename).name
    ext = Path(safe_name).suffix.lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            error_code="INVALID_EXTENSION",
            status_code=400
        )

    # 4. Declared MIME type validation
    normalized_mime = content_type.lower().split(";")[0].strip() if content_type else ""
    if normalized_mime not in ALLOWED_MIME_TYPES:
        raise ImageValidationError(
            detail=f"Unsupported MIME type '{normalized_mime}'. Allowed MIME types are: {', '.join(sorted(ALLOWED_MIME_TYPES.keys()))}.",
            error_code="INVALID_MIME_TYPE",
            status_code=400
        )

    # Verify extension matches declared MIME type
    if ext not in ALLOWED_MIME_TYPES[normalized_mime]:
        raise ImageValidationError(
            detail=f"File extension '{ext}' does not match declared MIME type '{normalized_mime}'.",
            error_code="MIME_EXTENSION_MISMATCH",
            status_code=400
        )

    # 5. True Image Decoding & Integrity Check
    try:
        # First pass: verify structural integrity
        img_stream = io.BytesIO(content)
        with Image.open(img_stream) as img:
            img.verify()

        # Second pass: read format and dimensions (verify() invalidates image object for inspection)
        img_stream.seek(0)
        with Image.open(img_stream) as img:
            detected_format = (img.format or "").upper()
            width, height = img.size

    except (UnidentifiedImageError, ValueError, SyntaxError) as e:
        raise ImageValidationError(
            detail=f"Malformed or corrupted image file could not be decoded: {str(e)}",
            error_code="MALFORMED_IMAGE",
            status_code=400
        )
    except Exception as e:
        raise ImageValidationError(
            detail=f"Failed to decode image: {str(e)}",
            error_code="IMAGE_DECODE_FAILED",
            status_code=400
        )

    # Ensure format matches allowed formats
    if detected_format not in FORMAT_TO_MIME:
        raise ImageValidationError(
            detail=f"Decoded image format '{detected_format}' is not an accepted format (JPEG, PNG, WEBP).",
            error_code="UNSUPPORTED_IMAGE_FORMAT",
            status_code=400
        )

    # Check that detected format matches the declared MIME type
    expected_mime = FORMAT_TO_MIME[detected_format]
    if expected_mime != normalized_mime:
        raise ImageValidationError(
            detail=f"Image contents identify as '{detected_format}' ({expected_mime}), which does not match declared MIME type '{normalized_mime}'.",
            error_code="IMAGE_CONTENT_MISMATCH",
            status_code=400
        )

    # 6. Image Dimension Validation
    if width <= 0 or height <= 0:
        raise ImageValidationError(
            detail=f"Invalid image dimensions: {width}x{height}. Both width and height must be positive.",
            error_code="INVALID_DIMENSIONS",
            status_code=400
        )

    return ValidatedImage(
        mime_type=normalized_mime,
        detected_format=detected_format,
        width=width,
        height=height,
        file_size=file_size
    )
