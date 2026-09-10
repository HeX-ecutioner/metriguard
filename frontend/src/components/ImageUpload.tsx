import React, { useRef, useState } from 'react';
import { apiClient } from '../api/client';
import type { PackageImage, Inspection, ApiError } from '../api/client';

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
    <div className="glass-card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h2>
          {lifecycleState === 'COMPLETED'
            ? 'Inspection Complete'
            : lifecycleState === 'PROCESSING'
              ? 'Processing Inspection'
              : 'Upload Package Image'}
        </h2>
        {inspectionId && lifecycleState !== 'IDLE' && (
          <span
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              padding: '0.35rem 0.75rem',
              background: 'rgba(59, 130, 246, 0.15)',
              color: 'var(--primary-color)',
              border: '1px solid var(--primary-color)',
              borderRadius: '9999px',
            }}
          >
            Inspection ID: #{inspectionId}
          </span>
        )}
      </div>

      {/* STATE A: Product Name Input (available only before starting) */}
      {(lifecycleState === 'IDLE' || lifecycleState === 'IMAGE_SELECTED') && (
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Product Name (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Masala Oats 500g"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid var(--glass-border)',
              borderRadius: '8px',
              color: 'var(--text-main)',
              fontSize: '0.95rem',
            }}
          />
        </div>
      )}

      {/* Validation / API Error Alert */}
      {validationError && (
        <div
          role="alert"
          style={{
            padding: '0.85rem 1rem',
            marginBottom: '1.25rem',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid var(--error-color)',
            borderRadius: '8px',
            color: '#fca5a5',
            fontSize: '0.9rem',
          }}
        >
          <strong>Error:</strong> {validationError}
        </div>
      )}

      {/* STATE A: IDLE Dropzone */}
      {lifecycleState === 'IDLE' && (
        <div
          className={`upload-area ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            cursor: 'pointer',
            padding: '2.5rem',
            textAlign: 'center',
            border: '2px dashed var(--glass-border)',
            borderRadius: '12px',
            background: dragActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
            transition: 'all 0.2s ease',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
            style={{ display: 'none' }}
            onChange={handleFileInputChange}
          />
          <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>📸</div>
          <h3 style={{ marginBottom: '0.5rem' }}>Drag & Drop Image Here</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Supported formats: JPEG, PNG, WebP (Max 10MB) • Paste from clipboard (Ctrl+V)
          </p>
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1.25rem', pointerEvents: 'none' }}
          >
            Browse Image
          </button>
        </div>
      )}

      {/* STATE B, C, D, ERROR: Preview & Controls */}
      {lifecycleState !== 'IDLE' && previewUrl && (
        <div className="fade-in">
          {/* Image Preview Container */}
          <div
            style={{
              position: 'relative',
              borderRadius: '12px',
              overflow: 'hidden',
              border: '1px solid var(--glass-border)',
              maxHeight: '360px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#000',
            }}
          >
            <img
              src={previewUrl}
              alt="Selected package label preview"
              style={{ maxWidth: '100%', maxHeight: '360px', objectFit: 'contain' }}
            />
          </div>

          {/* Selected File Details */}
          {selectedFile && (
            <div
              style={{
                marginTop: '0.75rem',
                fontSize: '0.85rem',
                color: 'var(--text-muted)',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>{selectedFile.name}</span>
              <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
            </div>
          )}

          {/* STATE C: PROCESSING Progress Indicators */}
          {lifecycleState === 'PROCESSING' && (
            <div style={{ marginTop: '1.25rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.85rem',
                  marginBottom: '0.35rem',
                }}
              >
                <span>Analyzing package declarations & legal metrology rules...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div
                style={{
                  width: '100%',
                  height: '8px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  borderRadius: '4px',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${uploadProgress}%`,
                    height: '100%',
                    background: 'var(--primary-color)',
                    transition: 'width 0.2s ease',
                  }}
                />
              </div>
            </div>
          )}

          {/* STATE D: COMPLETED Verified State */}
          {lifecycleState === 'COMPLETED' && uploadedImage && (
            <div
              style={{
                marginTop: '1.25rem',
                padding: '1rem',
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid var(--success-color)',
                borderRadius: '8px',
                fontSize: '0.9rem',
              }}
            >
              <h4 style={{ color: 'var(--success-color)', marginBottom: '0.5rem' }}>
                ✓ Inspection Completed Successfully
              </h4>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>Inspection ID:</strong> #{uploadedImage.inspection_id}
              </p>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>Dimensions:</strong> {uploadedImage.width} × {uploadedImage.height} px
              </p>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>File Size:</strong> {(uploadedImage.file_size / 1024).toFixed(1)} KB
              </p>
            </div>
          )}

          {/* Action Buttons based on lifecycle state */}
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
            {lifecycleState === 'IMAGE_SELECTED' && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={handleStartInspection}
                  style={{ flex: 1 }}
                >
                  Start Inspection
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleCancelSelection}
                  style={{ background: 'rgba(255, 255, 255, 0.1)' }}
                >
                  Cancel
                </button>
              </>
            )}

            {lifecycleState === 'PROCESSING' && (
              <button
                type="button"
                className="btn"
                onClick={handleCancelProcessing}
                style={{ background: 'rgba(255, 255, 255, 0.1)', width: '100%' }}
              >
                Return to upload screen
              </button>
            )}

            {lifecycleState === 'COMPLETED' && (
              <button
                type="button"
                className="btn"
                onClick={handleUploadAnotherImage}
                style={{ flex: 1 }}
              >
                + Upload Another Image
              </button>
            )}

            {lifecycleState === 'ERROR' && (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={handleStartInspection}
                  style={{ flex: 1 }}
                >
                  Retry Inspection
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleCancelSelection}
                  style={{ background: 'rgba(255, 255, 255, 0.1)' }}
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
