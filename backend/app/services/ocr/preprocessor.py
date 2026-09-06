"""
OpenCV Image Preprocessor for MetriGuard OCR Subsystem.
Implements stages 1-6 of the OCR pipeline:
1. Load image (from bytes or path)
2. Validate image (unreadable, corrupt, zero-dimension)
3. Optional aspect-ratio-preserving resizing
4. Grayscale conversion
5. Contrast enhancement (CLAHE)
6. Denoising (Bilateral filtering to preserve character edges)
"""

import io
from pathlib import Path
from typing import Tuple, Optional, Union
import cv2
import numpy as np
from PIL import Image

from app.models.ocr_schemas import (
    PreprocessingMetadata,
    UnreadableImageError,
    UnsupportedImageFormatError,
)


class ImagePreprocessor:
    """
    OpenCV-based image preprocessing pipeline engineered specifically for
    packaged commodity labels, preserving text boundary sharpness while eliminating noise.
    """

    def __init__(
        self,
        max_dimension: int = 2400,
        min_dimension: int = 15,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: Tuple[int, int] = (8, 8),
        denoise_method: str = "bilateral"
    ):
        self.max_dimension = max_dimension
        self.min_dimension = min_dimension
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
        self.denoise_method = denoise_method

    def load_image(self, input_data: Union[bytes, str, Path]) -> np.ndarray:
        """
        Stage 1: Load image from raw bytes or filesystem path into an OpenCV BGR numpy array.

        Args:
            input_data: Raw image bytes, or a filesystem path string/Path object.

        Returns:
            np.ndarray: Decoded OpenCV image in BGR format.

        Raises:
            UnreadableImageError: If the bytes cannot be decoded into an image.
        """
        if isinstance(input_data, (str, Path)):
            path = Path(input_data)
            if not path.is_file():
                raise UnreadableImageError(f"Image file does not exist at path: {path}")
            try:
                with open(path, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                raise UnreadableImageError(f"Failed to read image file from disk: {str(e)}")
        elif isinstance(input_data, (bytes, bytearray)):
            image_bytes = bytes(input_data)
        else:
            raise UnreadableImageError(f"Unsupported input type for image loading: {type(input_data)}")

        if not image_bytes or len(image_bytes) == 0:
            raise UnreadableImageError("Empty image data provided.")

        try:
            # First attempt: Direct OpenCV buffer decode
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Fallback attempt: Pillow decode (handles certain TIFF/WebP edge cases)
            if img is None:
                try:
                    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception:
                    img = None

            if img is None or not isinstance(img, np.ndarray) or img.size == 0:
                raise UnreadableImageError("Failed to decode image buffer as a valid image format.")

            return img
        except UnreadableImageError:
            raise
        except Exception as e:
            raise UnreadableImageError(f"Error decoding image: {str(e)}")

    def validate_image(self, image: np.ndarray) -> None:
        """
        Stage 2: Validate image structure, dimensions, and data type.

        Args:
            image: numpy image array.

        Raises:
            UnreadableImageError: If image is empty or invalid.
            UnsupportedImageFormatError: If dimensions or channels are unsupported.
        """
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            raise UnreadableImageError("Image array is empty or None.")

        if len(image.shape) < 2:
            raise UnsupportedImageFormatError("Image has less than 2 dimensions.")

        h, w = image.shape[:2]
        if h < self.min_dimension or w < self.min_dimension:
            raise UnsupportedImageFormatError(
                f"Image dimensions ({w}x{h}) are too small for text recognition (minimum is {self.min_dimension}px)."
            )

        if len(image.shape) == 3 and image.shape[2] not in (1, 3, 4):
            raise UnsupportedImageFormatError(f"Unsupported channel count: {image.shape[2]}")

    def resize_if_needed(self, image: np.ndarray) -> Tuple[np.ndarray, bool, Optional[int], Optional[int]]:
        """
        Stage 3: Aspect-ratio-preserving resize. Downscales oversized images to prevent
        memory exhaustion during OCR without distorting text typography.
        """
        h, w = image.shape[:2]
        if max(h, w) <= self.max_dimension:
            return image, False, None, None

        # Compute scaling ratio
        scale = self.max_dimension / float(max(h, w))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, True, new_w, new_h

    def convert_to_grayscale(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Stage 4: Grayscale conversion. Converts multi-channel BGR/RGBA to single-channel luminance.
        """
        if len(image.shape) == 2 or (len(image.shape) == 3 and image.shape[2] == 1):
            return image.copy(), False

        if len(image.shape) == 3:
            if image.shape[2] == 4:
                # RGBA/BGRA
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                # BGR
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return gray, True

        return image.copy(), False

    def enhance_contrast(self, gray_image: np.ndarray) -> Tuple[np.ndarray, bool, str]:
        """
        Stage 5: Contrast enhancement using Contrast Limited Adaptive Histogram Equalization (CLAHE).
        Prevents noise over-amplification in uniform regions while sharpening local text contrast.
        """
        if len(gray_image.shape) != 2:
            return gray_image.copy(), False, "none"

        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=self.clahe_grid_size
        )
        enhanced = clahe.apply(gray_image)
        return enhanced, True, "CLAHE"

    def denoise(self, gray_image: np.ndarray) -> Tuple[np.ndarray, bool, str]:
        """
        Stage 6: Denoising. Applies Bilateral Filtering to smooth packaging background grain
        while preserving high-frequency character edge gradients.
        """
        if len(gray_image.shape) != 2:
            return gray_image.copy(), False, "none"

        if self.denoise_method == "bilateral":
            # d=7, sigmaColor=50, sigmaSpace=50: effective text smoothing without blurring font strokes
            denoised = cv2.bilateralFilter(gray_image, d=7, sigmaColor=50, sigmaSpace=50)
            return denoised, True, "bilateral_filter"
        elif self.denoise_method == "gaussian":
            denoised = cv2.GaussianBlur(gray_image, (3, 3), 0)
            return denoised, True, "gaussian_blur"
        else:
            return gray_image.copy(), False, "none"

    def preprocess(self, input_data: Union[bytes, str, Path]) -> Tuple[np.ndarray, PreprocessingMetadata]:
        """
        Executes stages 1 through 6 sequentially, returning the processed image
        and full preprocessing audit metadata.

        Returns:
            Tuple[np.ndarray, PreprocessingMetadata]: The processed grayscale image and metadata.
        """
        # 1. Load image
        img = self.load_image(input_data)

        # 2. Validate image
        self.validate_image(img)
        orig_h, orig_w = img.shape[:2]

        # 3. Aspect-preserving resize
        img, resized, resized_w, resized_h = self.resize_if_needed(img)

        # 4. Grayscale conversion
        gray_img, grayscaled = self.convert_to_grayscale(img)

        # 5. Contrast enhancement (CLAHE)
        contrast_img, contrast_applied, contrast_method = self.enhance_contrast(gray_img)

        # 6. Denoising (Bilateral)
        denoised_img, denoise_applied, denoise_method = self.denoise(contrast_img)

        metadata = PreprocessingMetadata(
            original_width=orig_w,
            original_height=orig_h,
            resized=resized,
            resized_width=resized_w,
            resized_height=resized_h,
            grayscale=grayscaled,
            contrast_enhanced=contrast_applied,
            contrast_method=contrast_method if contrast_applied else None,
            denoised=denoise_applied,
            denoise_method=denoise_method if denoise_applied else None,
        )

        return denoised_img, metadata
