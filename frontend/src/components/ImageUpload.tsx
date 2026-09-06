import React, { useRef, useState } from 'react';
import { apiClient } from '../api/client';
import type { PackageImage, Inspection, ApiError } from '../api/client';

interface Props {
  onUploadSuccess?: (image: PackageImage, inspection: Inspection) => void;
  currentInspectionId?: number | null;
  onInspectionCreated?: (inspection: Inspection) => void;
}

const ImageUpload: React.FC<Props> = ({
  onUploadSuccess,
  currentInspectionId,
  onInspectionCreated
}) => {
  const [inspectionId, setInspectionId] = useState<number | null>(currentInspectionId || null);
  const [productName, setProductName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadedImage, setUploadedImage] = useState<PackageImage | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file: File) => {
    setValidationError(null);
    setUploadedImage(null);
    setSelectedFile(file);

    // Client-side preview
    const reader = new FileReader();
    reader.onload = (e) => setPreviewUrl(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleCreateInspection = async () => {
    setValidationError(null);
    try {
      const newInspection = await apiClient.createInspection({
        product_name: productName.trim() || undefined,
      });
      setInspectionId(newInspection.id);
      if (onInspectionCreated) {
        onInspectionCreated(newInspection);
      }
      return newInspection.id;
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setValidationError(apiErr.detail || 'Failed to create inspection session.');
      return null;
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setValidationError('Please select an image file first.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setValidationError(null);

    try {
      // Step 1: Ensure active inspection exists or create one
      let targetInspectionId = inspectionId;
      if (!targetInspectionId) {
        const createdId = await handleCreateInspection();
        if (!createdId) {
          setIsUploading(false);
          return;
        }
        targetInspectionId = createdId;
      }

      // Step 2: Upload image to inspection with progress callback
      const uploaded = await apiClient.uploadInspectionImage(
        targetInspectionId,
        selectedFile,
        (percentage) => setUploadProgress(percentage)
      );

      // Step 3: Fetch updated inspection to confirm real state (no fake success)
      const inspectionDetails = await apiClient.getInspection(targetInspectionId);

      setUploadedImage(uploaded);
      if (onUploadSuccess) {
        onUploadSuccess(uploaded, inspectionDetails);
      }
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setValidationError(apiErr.detail || 'Failed to upload image.');
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const resetSelection = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setValidationError(null);
    setUploadedImage(null);
    setUploadProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const startNewInspection = () => {
    setInspectionId(null);
    setProductName('');
    resetSelection();
  };

  return (
    <div className="glass-card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h2>Upload Package Image</h2>
        {inspectionId && (
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

      {/* Optional Product Name Input */}
      {!inspectionId && (
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Product Name (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Masala Oats 500g"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            disabled={isUploading}
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

      {/* Validation Error Alert */}
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
          <strong>Validation Error:</strong> {validationError}
        </div>
      )}

      {/* Upload Dropzone / Preview */}
      {!previewUrl ? (
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
            Supported formats: JPEG, PNG, WebP (Max 10MB)
          </p>
          <button
            type="button"
            className="btn"
            style={{ marginTop: '1.25rem', pointerEvents: 'none' }}
          >
            Browse Image
          </button>
        </div>
      ) : (
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
          {selectedFile && !uploadedImage && (
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

          {/* Upload Progress Bar */}
          {isUploading && (
            <div style={{ marginTop: '1rem' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '0.85rem',
                  marginBottom: '0.35rem',
                }}
              >
                <span>Uploading to server...</span>
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

          {/* Success Card (Real Verified State) */}
          {uploadedImage && (
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
                ✓ Image Uploaded Successfully
              </h4>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>Inspection ID:</strong> #{uploadedImage.inspection_id}
              </p>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>Image ID:</strong> #{uploadedImage.id}
              </p>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>Dimensions:</strong> {uploadedImage.width} × {uploadedImage.height} px
              </p>
              <p style={{ margin: '0.2rem 0' }}>
                <strong>File Size:</strong> {(uploadedImage.file_size / 1024).toFixed(1)} KB
              </p>
              <p style={{ margin: '0.2rem 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                <strong>Storage Path:</strong> {uploadedImage.file_path}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
            {!uploadedImage ? (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={handleUpload}
                  disabled={isUploading}
                  style={{ flex: 1 }}
                >
                  {isUploading ? 'Uploading...' : 'Upload Image'}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={resetSelection}
                  disabled={isUploading}
                  style={{ background: 'rgba(255, 255, 255, 0.1)' }}
                >
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="btn"
                  onClick={resetSelection}
                  style={{ flex: 1 }}
                >
                  Upload Another Image
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={startNewInspection}
                  style={{ background: 'rgba(255, 255, 255, 0.1)' }}
                >
                  Start New Inspection
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
