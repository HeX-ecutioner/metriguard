import React from 'react';
import type { Inspection } from '../api/client';
import { apiClient } from '../api/client';
import './styles/ResultsView.css';

interface Props {
  inspection: Inspection;
  onUploadAnotherImage?: () => void;
}

const DECLARATION_LABELS: Record<string, string> = {
  MRP: 'Maximum Retail Price (MRP)',
  NET_QUANTITY: 'Net Quantity',
  MANUFACTURER: 'Manufacturer Name & Address',
  PACKER: 'Packer Name & Address',
  IMPORTER: 'Importer Name & Address',
  COUNTRY_OF_ORIGIN: 'Country of Origin',
  PACKING_DATE: 'Date of Packing',
  MANUFACTURE_DATE: 'Date of Manufacture',
  BEST_BEFORE: 'Best Before Date',
  USE_BY: 'Use By / Expiry Date',
  CONSUMER_CARE: 'Consumer Care Details',
  UNIT_SALE_PRICE: 'Unit Sale Price (USP)',
  COMMODITY_NAME: 'Generic / Commodity Name',
};

const ResultsView: React.FC<Props> = ({ inspection, onUploadAnotherImage }) => {
  const [isGeneratingPdf, setIsGeneratingPdf] = React.useState(false);
  const [pdfError, setPdfError] = React.useState<string | null>(null);

  const confidencePercent = inspection.overall_confidence !== null && inspection.overall_confidence !== undefined
    ? (inspection.overall_confidence * 100).toFixed(1)
    : '0.0';

  const confidenceVal = inspection.overall_confidence ?? 0;
  const isManualReview = inspection.status === 'MANUAL_REVIEW';
  const isFailed = inspection.status === 'FAILED';
  const isCompleted = ['COMPLIANT', 'NON_COMPLIANT', 'MANUAL_REVIEW', 'FAILED'].includes(inspection.status);
  const primaryImage = inspection.images && inspection.images.length > 0 ? inspection.images[0] : null;
  const originalImageUrl = primaryImage ? apiClient.getImageFileUrl(inspection.id, primaryImage.id) : null;

  const handleDownloadPdf = async () => {
    if (isGeneratingPdf || !isCompleted) return;
    setIsGeneratingPdf(true);
    setPdfError(null);

    try {
      const blob = await apiClient.downloadInspectionReport(inspection.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `inspection_${inspection.id}_report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setPdfError(apiErr?.detail || 'Failed to generate PDF report. Please try again.');
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  return (
    <div className="glass-card fade-in results-container">
      {/* 1. Header & Status */}
      <div className="results-header">
        <div>
          <h2 className="results-title">
            Inspection Report #{inspection.id}
          </h2>
          {inspection.product_name && (
            <p className="results-product-sub">
              Product: <span className="results-product-name">{inspection.product_name}</span>
            </p>
          )}
        </div>
        <div className="results-actions">
          <span className={`status-badge status-${inspection.status}`}>
            {inspection.status.replace(/_/g, ' ')}
          </span>
          {originalImageUrl && (
            <a
              href={originalImageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn results-open-image-btn"
              title="Open the original uploaded image in a new tab"
            >
              Open Original Image ↗
            </a>
          )}
          {isCompleted && (
            <button
              type="button"
              className={`btn results-pdf-btn ${isGeneratingPdf ? 'generating' : ''}`}
              onClick={handleDownloadPdf}
              disabled={isGeneratingPdf}
              title="Download formal Legal Metrology compliance PDF report"
            >
              {isGeneratingPdf ? '⏳ Generating PDF...' : '📄 Generate PDF'}
            </button>
          )}
          {onUploadAnotherImage && (
            <button
              type="button"
              className="btn results-upload-another-btn"
              onClick={onUploadAnotherImage}
            >
              + Upload Another Image
            </button>
          )}
        </div>
      </div>

      {/* PDF Generation Error Banner */}
      {pdfError && (
        <div role="alert" className="results-error-banner">
          <span>⚠️ {pdfError}</span>
          <button
            type="button"
            onClick={() => setPdfError(null)}
            className="results-error-dismiss-btn"
          >
            ×
          </button>
        </div>
      )}

      {/* 2. Confidence Indicator */}
      <div>
        <div className="results-confidence-header">
          <span className="results-confidence-label">Overall Confidence Score</span>
          <span className="results-confidence-score">{confidencePercent}%</span>
        </div>
        <div className="results-confidence-track">
          <div
            className={`results-confidence-fill ${
              confidenceVal >= 0.8 ? 'fill-high' : confidenceVal >= 0.6 ? 'fill-medium' : 'fill-low'
            }`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* 3a. Processing Failure Alert */}
      {isFailed && (
        <div className="results-failed-card">
          <div className="results-alert-header">
            <span className="results-alert-icon">❌</span>
            <strong className="results-alert-title-error">Inspection Processing Failed</strong>
          </div>
          <p className="results-alert-text">
            {inspection.result?.summary || 'The inspection pipeline encountered an unrecoverable processing error (such as an image storage or database failure). This is distinct from a regulatory non-compliance finding.'}
          </p>
        </div>
      )}

      {/* 3b. Manual Review Warnings */}
      {isManualReview && (
        <div className="results-manual-card">
          <div className="results-alert-header">
            <span className="results-alert-icon">⚠️</span>
            <strong className="results-alert-title-warning">Manual Inspection Required</strong>
          </div>
          <p className="results-alert-text">
            {inspection.result?.summary || 'The package analysis requires manual verification by a Legal Metrology officer due to ambiguities, low extraction confidence, or unverified mandatory declarations.'}
          </p>
        </div>
      )}

      {/* 4. Regulatory Violations */}
      <div>
        <h3 className="results-section-title">
          Regulatory Violations ({inspection.violations?.length || 0})
        </h3>
        {inspection.violations && inspection.violations.length > 0 ? (
          <div className="results-violations-list">
            {inspection.violations.map((v) => (
              <div key={v.id} className="results-violation-card">
                <div className="results-violation-header">
                  <div className="results-violation-rule-info">
                    <span className="results-violation-rule-id">
                      {v.rule_id}
                    </span>
                    <span className="results-violation-version">
                      v{v.rule_version}
                    </span>
                  </div>
                  <span
                    className={`results-violation-severity ${
                      v.severity === 'CRITICAL' ? 'severity-critical' : 'severity-warning'
                    }`}
                  >
                    {v.severity}
                  </span>
                </div>
                <p className="results-violation-explanation">
                  {v.explanation}
                </p>
                <div className="results-violation-evidence">
                  {v.confidence !== null && v.confidence !== undefined && (
                    <span>Confidence: <strong>{(v.confidence * 100).toFixed(0)}%</strong></span>
                  )}
                  {v.evidence_image_id && (
                    <span>Evidence Image: <strong>#{v.evidence_image_id}</strong></span>
                  )}
                  {v.evidence_bounding_box && (
                    <span>Bounding Box: <strong>Available</strong></span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : inspection.status === 'COMPLIANT' ? (
          <div className="results-compliant-banner">
            <p className="results-compliant-text">
              ✓ All mandatory Legal Metrology (2011) declarations are present and compliant. No violations detected.
            </p>
          </div>
        ) : isFailed ? (
          <div className="results-failure-banner">
            Inspection could not be completed due to a processing failure.
          </div>
        ) : (
          <div className="results-clean-banner">
            No confirmed regulatory violations detected.
          </div>
        )}
      </div>

      {/* 5. Extracted Declarations */}
      <div>
        <h3 className="results-section-title">
          Extracted Package Declarations ({inspection.declarations?.length || 0})
        </h3>
        {inspection.declarations && inspection.declarations.length > 0 ? (
          <div className="results-declarations-grid">
            {inspection.declarations.map((decl) => (
              <div key={decl.id} className="results-declaration-card">
                <div className="results-declaration-type">
                  {DECLARATION_LABELS[decl.declaration_type] || decl.declaration_type}
                </div>
                <div className="results-declaration-value">
                  {decl.extracted_value}
                </div>
                <div className="results-declaration-meta">
                  <span>
                    Confidence: {decl.confidence ? `${(decl.confidence * 100).toFixed(0)}%` : 'N/A'}
                  </span>
                  {decl.bounding_box && (
                    <span className="results-bounding-box-tag">📍 Bounding Box</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="results-declarations-empty">
            No structured declarations extracted.
          </div>
        )}
      </div>

      {/* 6. Summary Footer */}
      {inspection.result?.summary && (
        <div className="results-summary-footer">
          <strong>Summary:</strong> {inspection.result.summary}
        </div>
      )}
    </div>
  );
};

export default ResultsView;
