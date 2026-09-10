import React, { useState, useEffect } from 'react';
import type { Inspection } from '../api/client';
import { apiClient } from '../api/client';
import ResultsView from './ResultsView';
import './styles/InspectionDetailView.css';

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
      <div className="glass-card fade-in detail-loading-card">
        <div className="spinner detail-spinner" />
        <p className="detail-loading-text">Loading inspection details...</p>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="glass-card fade-in detail-error-card">
        <p className="detail-error-text">
          {error || 'Inspection session not found.'}
        </p>
        <button className="btn" onClick={onBack}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="fade-in detail-container">
      {/* Top action row */}
      <div className="detail-top-bar">
        <button
          className="btn detail-back-btn"
          onClick={onBack}
        >
          ← Back to Dashboard
        </button>

        <span className="detail-timestamp">
          Session created {new Date(inspection.created_at).toLocaleString()}
        </span>
      </div>

      {/* Render full results and declarations */}
      <ResultsView inspection={inspection} />
    </div>
  );
};

export default InspectionDetailView;
