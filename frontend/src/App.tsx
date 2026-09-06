import { useState } from 'react';
import ImageUpload from './components/ImageUpload';
import ResultsView from './components/ResultsView';
import type { PackageImage, Inspection } from './api/client';

export interface Violation {
  rule_id: string;
  explanation: string;
  confidence: number;
}

export interface InspectionResult {
  status: 'COMPLIANT' | 'NON_COMPLIANT' | 'MANUAL_REVIEW';
  violations: Violation[];
  extracted_texts: string[];
  confidence_score: number;
}

function App() {
  const [activeInspection, setActiveInspection] = useState<Inspection | null>(null);
  const [inspectionResult, setInspectionResult] = useState<InspectionResult | null>(null);

  const handleUploadSuccess = (image: PackageImage, inspection: Inspection) => {
    setActiveInspection(inspection);

    // Populate inspection report from image analysis or inspection declarations
    if (image.status && image.confidence_score !== undefined && image.confidence_score !== null) {
      setInspectionResult({
        status: (image.status as 'COMPLIANT' | 'NON_COMPLIANT' | 'MANUAL_REVIEW') || 'MANUAL_REVIEW',
        confidence_score: image.confidence_score,
        extracted_texts: image.extracted_texts || [],
        violations: (image.violations || []).map((v) => ({
          rule_id: v.rule_id,
          explanation: v.explanation,
          confidence: v.confidence,
        })),
      });
    } else if (inspection.declarations && inspection.declarations.length > 0) {
      setInspectionResult({
        status: (inspection.status as 'COMPLIANT' | 'NON_COMPLIANT' | 'MANUAL_REVIEW') || 'MANUAL_REVIEW',
        confidence_score: inspection.overall_confidence || 0,
        extracted_texts: inspection.declarations.map((d) => d.extracted_value),
        violations: (inspection.violations || []).map((v) => ({
          rule_id: v.rule_id,
          explanation: v.explanation,
          confidence: v.confidence || 1.0,
        })),
      });
    }
  };

  const handleInspectionCreated = (inspection: Inspection) => {
    setActiveInspection(inspection);
    setInspectionResult(null);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>MetriGuard</h1>
        <p>AI-Assisted Legal Metrology Compliance Inspection Platform</p>
      </header>

      <main className="app-grid fade-in">
        <section className="upload-column" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <ImageUpload
            onUploadSuccess={handleUploadSuccess}
            currentInspectionId={activeInspection?.id}
            onInspectionCreated={handleInspectionCreated}
          />

          {activeInspection && activeInspection.images && activeInspection.images.length > 0 && (
            <section className="glass-card">
              <h3 style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Inspection Session #{activeInspection.id}</span>
                <span
                  style={{
                    fontSize: '0.8rem',
                    color: 'var(--primary-color)',
                    padding: '0.2rem 0.6rem',
                    borderRadius: '9999px',
                    background: 'rgba(59, 130, 246, 0.1)',
                    border: '1px solid var(--primary-color)',
                  }}
                >
                  {activeInspection.status}
                </span>
              </h3>
              {activeInspection.product_name && (
                <p style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>
                  <strong>Product:</strong> {activeInspection.product_name}
                </p>
              )}
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.75rem' }}>
                Attached Images ({activeInspection.images.length}):
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '0.75rem' }}>
                {activeInspection.images.map((img) => (
                  <div
                    key={img.id}
                    style={{
                      padding: '0.75rem',
                      background: 'rgba(15, 23, 42, 0.6)',
                      borderRadius: '8px',
                      border: '1px solid var(--glass-border)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <p style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '0.25rem' }}>
                      {img.original_filename}
                    </p>
                    <p style={{ color: 'var(--text-muted)' }}>{img.width} × {img.height} px</p>
                    <p style={{ color: 'var(--text-muted)' }}>{(img.file_size / 1024).toFixed(1)} KB</p>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.25rem' }}>ID #{img.id}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </section>

        <section className="results-column">
          {inspectionResult ? (
            <ResultsView result={inspectionResult} />
          ) : (
            <div
              className="glass-card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                minHeight: '320px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                padding: '2.5rem 1.5rem',
              }}
            >
              <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.7 }}>📋</div>
              <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-main)' }}>Inspection Report</h3>
              <p style={{ maxWidth: '360px', fontSize: '0.9rem', lineHeight: '1.5' }}>
                Upload a packaged commodity label to trigger automated OCR extraction and Legal Metrology (2011) compliance verification.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;

