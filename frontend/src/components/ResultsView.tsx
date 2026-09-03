import React from 'react';
import type { InspectionResult } from '../App';

interface Props {
  result: InspectionResult;
}

const ResultsView: React.FC<Props> = ({ result }) => {
  return (
    <div className="glass-card fade-in">
      <h2 style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Inspection Report
        <span className={`status-badge status-${result.status}`}>
          {result.status.replace('_', ' ')}
        </span>
      </h2>
      
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Confidence Score</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ flex: 1, height: '8px', background: 'var(--glass-border)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ 
              height: '100%', 
              width: `${result.confidence_score * 100}%`,
              background: result.confidence_score > 0.8 ? 'var(--success-color)' : result.confidence_score > 0.5 ? 'var(--warning-color)' : 'var(--error-color)',
              transition: 'width 1s ease-out'
            }} />
          </div>
          <span style={{ fontWeight: 600 }}>{(result.confidence_score * 100).toFixed(1)}%</span>
        </div>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>Extracted Texts (Raw)</h3>
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          {result.extracted_texts && result.extracted_texts.length > 0 ? (
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {result.extracted_texts.map((text, idx) => (
                <li key={idx} style={{ paddingLeft: '1rem', borderLeft: '2px solid var(--primary-color)' }}>{text}</li>
              ))}
            </ul>
          ) : (
            <p>No text detected.</p>
          )}
        </div>
      </div>

      <div>
        <h3 style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>Rule Violations</h3>
        {result.violations && result.violations.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {result.violations.map((violation, idx) => (
              <div key={idx} style={{ 
                padding: '1rem', 
                borderRadius: '8px', 
                borderLeft: '4px solid var(--error-color)',
                background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.1) 0%, transparent 100%)'
              }}>
                <div style={{ fontWeight: 600, color: 'var(--error-color)', marginBottom: '0.25rem' }}>
                  {violation.rule_id}
                </div>
                <p>{violation.explanation}</p>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '1rem', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', textAlign: 'center' }}>
            <p style={{ color: 'var(--success-color)', fontWeight: 500 }}>No violations detected. Package meets requirements.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsView;
