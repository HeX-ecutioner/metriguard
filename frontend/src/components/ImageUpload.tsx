import React, { useRef, useState } from 'react';

interface Props {
  onUpload: (file: File) => void;
  isProcessing: boolean;
}

const ImageUpload: React.FC<Props> = ({ onUpload, isProcessing }) => {
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file: File) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setPreview(e.target?.result as string);
      reader.readAsDataURL(file);
      onUpload(file);
    } else {
      alert("Please upload an image file");
    }
  };

  return (
    <div className="glass-card">
      <h2 style={{ marginBottom: '1.5rem' }}>Upload Package Image</h2>
      
      {!preview ? (
        <div 
          className={`upload-area ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            ref={fileInputRef}
            type="file" 
            accept="image/*" 
            style={{ display: 'none' }} 
            onChange={handleChange}
          />
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📸</div>
          <h3>Drag & Drop Image Here</h3>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>or click to browse</p>
        </div>
      ) : (
        <div className="fade-in">
          <div style={{ position: 'relative', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--glass-border)' }}>
            <img src={preview} alt="Preview" style={{ width: '100%', display: 'block' }} />
            {isProcessing && (
              <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                  <div className="spinner" style={{ width: '40px', height: '40px', border: '4px solid var(--glass-border)', borderTopColor: 'var(--primary-color)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                  <p>Processing with AI...</p>
                </div>
              </div>
            )}
          </div>
          {!isProcessing && (
            <button className="btn" style={{ width: '100%', marginTop: '1rem' }} onClick={() => setPreview(null)}>
              Upload New Image
            </button>
          )}
        </div>
      )}
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

export default ImageUpload;
