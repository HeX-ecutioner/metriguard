import React, { useRef, useState } from 'react';
import { apiClient } from '../api/client';
import type { PackageImage, Inspection, ApiError } from '../api/client';
import './styles/ImageUpload.css';

export type UploadLifecycleState = 'IDLE' | 'IMAGE_SELECTED' | 'PROCESSING' | 'COMPLETED' | 'ERROR';

interface Props {
  onUploadSuccess?: (image: PackageImage, inspection: Inspection) => void;
  currentInspectionId?: number | null;
  onInspectionCreated?: (inspection: Inspection) => void;
  onUploadAnotherImage?: () => void;
}

const ImageUpload: React.FC<Props> = ({
  onUploadSuccess,
  currentInspectionId,
  onInspectionCreated,
  onUploadAnotherImage,
}) => {
  const [lifecycleState, setLifecycleState] = useState<UploadLifecycleState>('IDLE');
  const [inspectionId, setInspectionId] = useState<number | null>(currentInspectionId || null);
  const [productName, setProductName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadedImage, setUploadedImage] = useState<PackageImage | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Guard against stale asynchronous responses from previous/cancelled requests
  const activeRequestId = useRef<number>(0);
  // Guard against concurrent / double-click inspection creation
  const isSubmittingRef = useRef<boolean>(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (lifecycleState === 'PROCESSING') return;
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (lifecycleState === 'PROCESSING') return;
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  // Clipboard Paste Support (Ctrl+V / Cmd+V)
  React.useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      // Don't intercept paste if user is typing into text inputs/textareas
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') && target.getAttribute('type') !== 'file') {
        // If the target is a text input, let normal text paste proceed
        return;
      }

      if (lifecycleState === 'PROCESSING') return;

      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            // Provide a default name if pasted file has none or generic name
            const namedFile = file.name && file.name !== 'image.png'
              ? file
              : new File([file], `pasted_image_${Date.now()}.${file.type.split('/')[1] || 'png'}`, { type: file.type });
            handleFileSelected(namedFile);
            break;
          }
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [lifecycleState]);

  // STATE B: IMAGE_SELECTED - Local selection only. Zero API calls, zero DB rows.
  const handleFileSelected = (file: File) => {
    setValidationError(null);
    setUploadedImage(null);
    setSelectedFile(file);
    setUploadProgress(0);

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target?.result as string);
      setLifecycleState('IMAGE_SELECTED');
    };
    reader.readAsDataURL(file);
  };

  // Pre-upload cancel: Return to STATE A (IDLE) with zero server calls
  const handleCancelSelection = () => {
    // Invalidate any pending async callbacks
    activeRequestId.current += 1;
    isSubmittingRef.current = false;
    setSelectedFile(null);
    setPreviewUrl(null);
    setValidationError(null);
    setUploadedImage(null);
    setUploadProgress(0);
    setLifecycleState('IDLE');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Abandon/Cancel in-flight processing safely
  const handleCancelProcessing = () => {
    activeRequestId.current += 1; // Invalidate any response from this request
    isSubmittingRef.current = false;
    handleCancelSelection();
  };

  // STATE C: PROCESSING - Only begins when user clicks "Start inspection"
  const handleStartInspection = async () => {
    if (!selectedFile) {
      setValidationError('Please select an image file first.');
      return;
    }

    if (isSubmittingRef.current || lifecycleState === 'PROCESSING') {
      return;
    }
    isSubmittingRef.current = true;

    const currentReq = ++activeRequestId.current;
    setLifecycleState('PROCESSING');
    setUploadProgress(0);
    setValidationError(null);

    try {
      // 1. Create a brand-new inspection session for this upload
      const newInspection = await apiClient.createInspection({
        product_name: productName.trim() || undefined,
      });

      // Check for stale response
      if (activeRequestId.current !== currentReq) return;

      setInspectionId(newInspection.id);
      if (onInspectionCreated) {
        onInspectionCreated(newInspection);
      }

      // 2. Upload exactly one image for this new inspection session
      const uploaded = await apiClient.uploadInspectionImage(
        newInspection.id,
        selectedFile,
        (percentage) => {
          if (activeRequestId.current === currentReq) {
            setUploadProgress(percentage);
          }
        }
      );

      // Check for stale response
      if (activeRequestId.current !== currentReq) return;

      // 3. Retrieve final synthesized inspection record
      const inspectionDetails = await apiClient.getInspection(newInspection.id);

      // Check for stale response
      if (activeRequestId.current !== currentReq) return;

      // STATE D: COMPLETED - Single result associated with this new inspection ID
      setUploadedImage(uploaded);
      setLifecycleState('COMPLETED');
      if (onUploadSuccess) {
        onUploadSuccess(uploaded, inspectionDetails);
      }
    } catch (err: unknown) {
      if (activeRequestId.current !== currentReq) return;

      const apiErr = err as ApiError;
      setValidationError(apiErr.detail || 'Failed to complete inspection.');
      setLifecycleState('ERROR');
      setUploadProgress(0);
    } finally {
      isSubmittingRef.current = false;
    }
  };

  // STATE E: UPLOAD_ANOTHER_IMAGE - Resets everything to IDLE for a brand-new session
  const handleUploadAnotherImage = () => {
    activeRequestId.current += 1;
    isSubmittingRef.current = false;
    setSelectedFile(null);
    setPreviewUrl(null);
    setValidationError(null);
    setUploadedImage(null);
    setUploadProgress(0);
    setInspectionId(null);
    setProductName('');
    setLifecycleState('IDLE');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (onUploadAnotherImage) {
      onUploadAnotherImage();
    }
  };

  return (
    <div className="glass-card upload-container">
      <div className="upload-header">
        <h2>
          {lifecycleState === 'COMPLETED'
            ? 'Inspection Complete'
            : lifecycleState === 'PROCESSING'
              ? 'Processing Inspection'
              : 'Upload Package Image'}
        </h2>
        {inspectionId && lifecycleState !== 'IDLE' && (
          <span className="upload-inspection-tag">
            Inspection ID: #{inspectionId}
          </span>
        )}
      </div>

      {/* STATE A: Product Name Input (available only before starting) */}
      {(lifecycleState === 'IDLE' || lifecycleState === 'IMAGE_SELECTED') && (
        <div className="upload-input-group">
          <label className="upload-label">
            Product Name (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Masala Oats 500g"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            className="upload-text-input"
          />
        </div>
      )}

      {/* Validation / API Error Alert */}
      {validationError && (
        <div role="alert" className="upload-error-alert">
          <strong>Error:</strong> {validationError}
        </div>
      )}

      {/* STATE A: IDLE Dropzone */}
      {lifecycleState === 'IDLE' && (
        <div
          className={`upload-area upload-dropzone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            className="upload-file-input"
            onChange={handleFileInputChange}
          />
          <div className="upload-icon">📸</div>
          <h3 className="upload-dropzone-title">Drag & Drop Image Here</h3>
          <p className="upload-dropzone-subtitle">
            Supported formats: JPEG, PNG, WebP (Max 10MB) • Paste from clipboard (Ctrl+V)
          </p>
          <button
            type="button"
            className="btn upload-browse-btn"
          >
            Browse Image
          </button>
        </div>
      )}

      {/* STATE B, C, D, ERROR: Preview & Controls */}
      {lifecycleState !== 'IDLE' && previewUrl && (
        <div className="fade-in">
          {/* Image Preview Container */}
          <div className="upload-preview-container">
            <img
              src={previewUrl}
              alt="Selected package label preview"
              className="upload-preview-image"
            />
          </div>

          {/* Selected File Details */}
          {selectedFile && (
            <div className="upload-file-details">
              <span>{selectedFile.name}</span>
              <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
            </div>
          )}

          {/* STATE C: PROCESSING Progress Indicators */}
          {lifecycleState === 'PROCESSING' && (
            <div className="upload-progress-container">
              <div className="upload-progress-labels">
                <span>Analyzing package declarations & legal metrology rules...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="upload-progress-track">
                <div
                  className="upload-progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* STATE D: COMPLETED Verified State */}
          {lifecycleState === 'COMPLETED' && uploadedImage && (
            <div className="upload-completed-box">
              <h4 className="upload-completed-title">
                ✓ Inspection Completed Successfully
              </h4>
              <p className="upload-completed-row">
                <strong>Inspection ID:</strong> #{uploadedImage.inspection_id}
              </p>
              <p className="upload-completed-row">
                <strong>Dimensions:</strong> {uploadedImage.width} × {uploadedImage.height} px
              </p>
              <p className="upload-completed-row">
                <strong>File Size:</strong> {(uploadedImage.file_size / 1024).toFixed(1)} KB
              </p>
            </div>
          )}

          {/* Action Buttons based on lifecycle state */}
          <div className="upload-actions">
            {lifecycleState === 'IMAGE_SELECTED' && (
              <>
                <button
                  type="button"
                  className="btn upload-btn-primary"
                  onClick={handleStartInspection}
                >
                  Start Inspection
                </button>
                <button
                  type="button"
                  className="btn upload-btn-secondary"
                  onClick={handleCancelSelection}
                >
                  Cancel
                </button>
              </>
            )}

            {lifecycleState === 'PROCESSING' && (
              <button
                type="button"
                className="btn upload-btn-cancel-processing"
                onClick={handleCancelProcessing}
              >
                Return to upload screen
              </button>
            )}

            {lifecycleState === 'COMPLETED' && (
              <button
                type="button"
                className="btn upload-btn-primary"
                onClick={handleUploadAnotherImage}
              >
                + Upload Another Image
              </button>
            )}

            {lifecycleState === 'ERROR' && (
              <>
                <button
                  type="button"
                  className="btn upload-btn-primary"
                  onClick={handleStartInspection}
                >
                  Retry Inspection
                </button>
                <button
                  type="button"
                  className="btn upload-btn-secondary"
                  onClick={handleCancelSelection}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ImageUpload;
