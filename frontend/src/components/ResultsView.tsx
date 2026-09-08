import React from 'react';
import type { Inspection } from '../api/client';
import { apiClient } from '../api/client';

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
  const confidencePercent = inspection.overall_confidence !== null && inspection.overall_confidence !== undefined
    ? (inspection.overall_confidence * 100).toFixed(1)
    : '0.0';

  const confidenceVal = inspection.overall_confidence ?? 0;
  const isManualReview = inspection.status === 'MANUAL_REVIEW';
  const isFailed = inspection.status === 'FAILED';
  const primaryImage = inspection.images && inspection.images.length > 0 ? inspection.images[0] : null;
  const originalImageUrl = primaryImage ? apiClient.getImageFileUrl(inspection.id, primaryImage.id) : null;

  return (
    <div className="glass-card fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* 1. Header & Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid var(--glass-border)', paddingBottom: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>
            Inspection Report #{inspection.id}
          </h2>
          {inspection.product_name && (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Product: <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>{inspection.product_name}</span>
            </p>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span className={`status-badge status-${inspection.status}`}>
            {inspection.status.replace(/_/g, ' ')}
          </span>
          {originalImageUrl && (
            <a
              href={originalImageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn"
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem', textDecoration: 'none' }}
              title="Open the original uploaded image in a new tab"
            >
              Open Original Image ↗
            </a>
          )}
          {onUploadAnotherImage && (
            <button
              type="button"
              className="btn"
              onClick={onUploadAnotherImage}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem', background: 'rgba(59, 130, 246, 0.2)', borderColor: 'var(--primary-color)' }}
            >
              + Upload Another Image
            </button>
          )}
        </div>
      </div>

      {/* 2. Confidence Indicator */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>Overall Confidence Score</span>
          <span style={{ fontWeight: 600 }}>{confidencePercent}%</span>
        </div>
        <div style={{ height: '8px', background: 'var(--glass-border)', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${confidencePercent}%`,
              background: confidenceVal >= 0.8 ? 'var(--success-color)' : confidenceVal >= 0.6 ? 'var(--warning-color)' : 'var(--error-color)',
              transition: 'width 0.8s ease-out',
            }}
          />
        </div>
      </div>

      {/* 3a. Processing Failure Alert */}
      {isFailed && (
        <div
          style={{
            padding: '1rem 1.25rem',
            borderRadius: '8px',
            borderLeft: '4px solid var(--error-color)',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>❌</span>
            <strong style={{ color: 'var(--error-color)' }}>Inspection Processing Failed</strong>
          </div>
          <p style={{ fontSize: '0.9rem', lineHeight: '1.5', color: 'var(--text-main)' }}>
            {inspection.result?.summary || 'The inspection pipeline encountered an unrecoverable processing error (such as an image storage or database failure). This is distinct from a regulatory non-compliance finding.'}
          </p>
        </div>
      )}

      {/* 3b. Manual Review Warnings */}
      {isManualReview && (
        <div
          style={{
            padding: '1rem 1.25rem',
            borderRadius: '8px',
            borderLeft: '4px solid var(--warning-color)',
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>⚠️</span>
            <strong style={{ color: 'var(--warning-color)' }}>Manual Inspection Required</strong>
          </div>
          <p style={{ fontSize: '0.9rem', lineHeight: '1.5', color: 'var(--text-main)' }}>
            {inspection.result?.summary || 'The package analysis requires manual verification by a Legal Metrology officer due to ambiguities, low extraction confidence, or unverified mandatory declarations.'}
          </p>
        </div>
      )}

      {/* 4. Regulatory Violations */}
      <div>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--text-muted)' }}>
          Regulatory Violations ({inspection.violations?.length || 0})
        </h3>
        {inspection.violations && inspection.violations.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {inspection.violations.map((v) => (
              <div
                key={v.id}
                style={{
                  padding: '1rem',
                  borderRadius: '8px',
                  borderLeft: '4px solid var(--error-color)',
                  background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.12) 0%, rgba(15, 23, 42, 0.4) 100%)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, color: 'var(--error-color)', fontSize: '0.95rem' }}>
                      {v.rule_id}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.08)', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                      v{v.rule_version}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                      background: v.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)',
                      color: v.severity === 'CRITICAL' ? 'var(--error-color)' : 'var(--warning-color)',
                    }}
                  >
                    {v.severity}
                  </span>
                </div>
                <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem', lineHeight: '1.4' }}>
                  {v.explanation}
                </p>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
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
          <div
            style={{
              padding: '1rem',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              textAlign: 'center',
            }}
          >
            <p style={{ color: 'var(--success-color)', fontWeight: 500 }}>
              ✓ All mandatory Legal Metrology (2011) declarations are present and compliant. No violations detected.
            </p>
          </div>
        ) : isFailed ? (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              textAlign: 'center',
              color: '#fca5a5',
              fontSize: '0.85rem',
            }}
          >
            Inspection could not be completed due to a processing failure.
          </div>
        ) : (
          <div
            style={{
              padding: '0.75rem',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--glass-border)',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
            }}
          >
            No confirmed regulatory violations detected.
          </div>
        )}
      </div>

      {/* 5. Extracted Declarations */}
      <div>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', color: 'var(--text-muted)' }}>
          Extracted Package Declarations ({inspection.declarations?.length || 0})
        </h3>
        {inspection.declarations && inspection.declarations.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
            {inspection.declarations.map((decl) => (
              <div
                key={decl.id}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid var(--glass-border)',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem', fontWeight: 600 }}>
                  {DECLARATION_LABELS[decl.declaration_type] || decl.declaration_type}
                </div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.4rem', wordBreak: 'break-word' }}>
                  {decl.extracted_value}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>
                    Confidence: {decl.confidence ? `${(decl.confidence * 100).toFixed(0)}%` : 'N/A'}
                  </span>
                  {decl.bounding_box && (
                    <span style={{ color: 'var(--primary-color)' }}>📍 Bounding Box</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div
            style={{
              padding: '1rem',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--glass-border)',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.85rem',
            }}
          >
            No structured declarations extracted.
          </div>
        )}
      </div>

      {/* 6. Summary Footer */}
      {inspection.result?.summary && (
        <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <strong>Summary:</strong> {inspection.result.summary}
        </div>
      )}
    </div>
  );
};

export default ResultsView;
