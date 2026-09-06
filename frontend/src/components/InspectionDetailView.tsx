import React, { useState, useEffect } from 'react';
import type { Inspection } from '../api/client';
import { apiClient } from '../api/client';
import ResultsView from './ResultsView';

interface Props {
  inspectionId?: number;
  initialInspection?: Inspection | null;
  onBack: () => void;
}

const InspectionDetailView: React.FC<Props> = ({
  inspectionId,
  initialInspection,
  onBack,
}) => {
  const [fetchedInspection, setFetchedInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState<boolean>(!initialInspection && !!inspectionId);
  const [error, setError] = useState<string | null>(null);

  const inspection = initialInspection || fetchedInspection;

  useEffect(() => {
    if (initialInspection || !inspectionId) {
      return;
    }

    let cancelled = false;
    apiClient
      .getInspection(inspectionId)
      .then((data) => {
        if (!cancelled) {
          setFetchedInspection(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const apiErr = err as { detail?: string };
          setError(apiErr?.detail || `Failed to load inspection #${inspectionId}`);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [inspectionId, initialInspection]);


  if (loading) {
    return (
      <div className="glass-card fade-in" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
        <div className="spinner" style={{ margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-muted)' }}>Loading inspection details...</p>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="glass-card fade-in" style={{ textAlign: 'center', padding: '2.5rem 1.5rem' }}>
        <p style={{ color: 'var(--error-color)', fontWeight: 600, marginBottom: '1rem' }}>
          {error || 'Inspection session not found.'}
        </p>
        <button className="btn" onClick={onBack}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top action row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          className="btn"
          onClick={onBack}
          style={{
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid var(--glass-border)',
            boxShadow: 'none',
          }}
        >
          ← Back to Dashboard
        </button>

        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Session created {new Date(inspection.created_at).toLocaleString()}
        </span>
      </div>

      {/* Render full results and declarations */}
      <ResultsView inspection={inspection} />
    </div>
  );
};

export default InspectionDetailView;
