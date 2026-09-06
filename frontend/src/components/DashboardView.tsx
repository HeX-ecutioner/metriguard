import React, { useState, useEffect, useCallback } from 'react';
import type { DashboardStats, Inspection } from '../api/client';
import { apiClient } from '../api/client';

interface Props {
  onSelectInspection: (inspectionId: number) => void;
  onNewInspection: () => void;
}

const DashboardView: React.FC<Props> = ({ onSelectInspection, onNewInspection }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // History search and filter state
  const [historySearch, setHistorySearch] = useState<string>('');
  const [historyStatus, setHistoryStatus] = useState<string>('ALL');
  const [historyList, setHistoryList] = useState<Inspection[]>([]);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getDashboardStats();
      setStats(data);
      setHistoryList(data.recent_inspections || []);
    } catch (err: any) {
      setError(err?.detail || 'Failed to connect to backend inspection service.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // Handle history filtering
  const handleFilterHistory = useCallback(async (searchVal: string, statusVal: string) => {
    setHistoryLoading(true);
    try {
      const filtered = await apiClient.listInspections({
        search: searchVal.trim() || undefined,
        status: statusVal !== 'ALL' ? statusVal : undefined,
        limit: 50,
      });
      setHistoryList(filtered);
    } catch {
      // Keep previous list on search error
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setHistorySearch(val);
    handleFilterHistory(val, historyStatus);
  };

  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setHistoryStatus(val);
    handleFilterHistory(historySearch, val);
  };

  // 1. Loading State
  if (loading) {
    return (
      <div
        className="glass-card fade-in"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '360px',
          textAlign: 'center',
          gap: '1rem',
        }}
        data-testid="dashboard-loading"
      >
        <div className="spinner" />
        <h3 style={{ fontWeight: 500, color: 'var(--text-main)' }}>Loading MetriGuard Dashboard...</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          Retrieving live compliance statistics and inspection records from database.
        </p>
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div
        className="glass-card fade-in"
        style={{
          textAlign: 'center',
          padding: '3rem 1.5rem',
          border: '1px solid rgba(239, 68, 68, 0.4)',
        }}
        data-testid="dashboard-error"
      >
        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>⚠️</div>
        <h3 style={{ color: 'var(--error-color)', marginBottom: '0.5rem' }}>Failed to Load Dashboard</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', maxWidth: '420px', margin: '0 auto 1.5rem' }}>
          {error}
        </p>
        <button className="btn" onClick={fetchStats} style={{ background: 'var(--primary-color)' }}>
          🔄 Retry Connection
        </button>
      </div>
    );
  }

  // 3. Empty State
  if (!stats || stats.total_inspections === 0) {
    return (
      <div
        className="glass-card fade-in"
        style={{
          textAlign: 'center',
          padding: '3.5rem 2rem',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem',
        }}
        data-testid="dashboard-empty"
      >
        <div style={{ fontSize: '3rem', opacity: 0.8 }}>📦</div>
        <h3 style={{ fontSize: '1.4rem' }}>No Inspections Recorded Yet</h3>
        <p style={{ color: 'var(--text-muted)', maxWidth: '440px', fontSize: '0.95rem', lineHeight: '1.5' }}>
          The database currently contains no packaged commodity inspections. Upload a package label image to begin automated Legal Metrology compliance verification.
        </p>
        <button className="btn" onClick={onNewInspection} style={{ marginTop: '0.5rem' }}>
          ⚡ Start First Inspection
        </button>
      </div>
    );
  }

  // Calculate highest violation count for meter percentage calculation
  const maxViolationCount = stats.top_violations.length > 0
    ? Math.max(...stats.top_violations.map((v) => v.count), 1)
    : 1;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }} data-testid="dashboard-content">
      {/* 1-4. Stat Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.25rem',
        }}
        data-testid="metric-cards"
      >
        {/* Card 1: Total Inspections */}
        <div
          className="glass-card"
          style={{
            padding: '1.5rem',
            borderLeft: '4px solid var(--primary-color)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase' }}>
            Total Inspections
          </span>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--text-main)' }}>
            {stats.total_inspections}
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>All evaluated packages</span>
        </div>

        {/* Card 2: Compliant */}
        <div
          className="glass-card"
          style={{
            padding: '1.5rem',
            borderLeft: '4px solid var(--success-color)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase' }}>
            Compliant
          </span>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--success-color)' }}>
            {stats.compliant_inspections}
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            {stats.total_inspections > 0
              ? `${((stats.compliant_inspections / stats.total_inspections) * 100).toFixed(1)}% of total`
              : '0%'}
          </span>
        </div>

        {/* Card 3: Non-Compliant */}
        <div
          className="glass-card"
          style={{
            padding: '1.5rem',
            borderLeft: '4px solid var(--error-color)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase' }}>
            Non-Compliant
          </span>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--error-color)' }}>
            {stats.non_compliant_inspections}
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            {stats.total_inspections > 0
              ? `${((stats.non_compliant_inspections / stats.total_inspections) * 100).toFixed(1)}% violations`
              : '0%'}
          </span>
        </div>

        {/* Card 4: Manual Review */}
        <div
          className="glass-card"
          style={{
            padding: '1.5rem',
            borderLeft: '4px solid var(--warning-color)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase' }}>
            Manual Review
          </span>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, color: 'var(--warning-color)' }}>
            {stats.manual_review_inspections}
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Requires officer review</span>
        </div>
      </div>

      {/* Mid-Row: Top Violation Types & Quick Actions */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1.5rem',
        }}
      >
        {/* Section 6: Top Violation Types */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.15rem' }}>Top Regulatory Violation Types</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>LMR 2011 Enforcements</span>
          </div>

          {stats.top_violations.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic', padding: '1rem 0' }}>
              No violations recorded in the database.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }} data-testid="top-violations-list">
              {stats.top_violations.map((violation) => {
                const percent = Math.round((violation.count / maxViolationCount) * 100);
                return (
                  <div key={violation.rule_id} style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {violation.rule_id}
                        <span style={{ marginLeft: '0.5rem', fontWeight: 400, color: 'var(--text-muted)' }}>
                          ({violation.title})
                        </span>
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            padding: '0.15rem 0.4rem',
                            borderRadius: '4px',
                            background: violation.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: violation.severity === 'CRITICAL' ? 'var(--error-color)' : 'var(--warning-color)',
                            fontWeight: 600,
                          }}
                        >
                          {violation.severity}
                        </span>
                        <strong style={{ color: 'var(--text-main)' }}>{violation.count}</strong>
                      </div>
                    </div>
                    {/* CSS Progress Meter Bar */}
                    <div
                      style={{
                        height: '6px',
                        background: 'rgba(255, 255, 255, 0.08)',
                        borderRadius: '3px',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          height: '100%',
                          width: `${percent}%`,
                          background: 'linear-gradient(90deg, #f59e0b, #ef4444)',
                          borderRadius: '3px',
                          transition: 'width 0.6s ease',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Action / Pipeline Quick Card */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '1.25rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', marginBottom: '0.5rem' }}>New Package Inspection</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Run automated Legal Metrology (2011) compliance verification on a new packaged commodity label.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <li>✓ OCR detection of declarations & units</li>
              <li>✓ Deterministic verification across 6 active rules</li>
              <li>✓ Traceable evidence bounding boxes & image links</li>
            </ul>
          </div>

          <button className="btn" onClick={onNewInspection} style={{ width: '100%', padding: '0.85rem' }}>
            ⚡ Launch Inspection Session
          </button>
        </div>
      </div>

      {/* Section 5: Recent Inspections Table */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem' }}>Recent Inspections</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Latest 10 package inspection runs stored in database
            </p>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }} data-testid="recent-inspections-table">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--glass-border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.75rem 0.5rem' }}>ID</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Product / Commodity</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Status</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Confidence</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Violations</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Date</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_inspections.map((insp) => {
                const confPercent = insp.overall_confidence !== null && insp.overall_confidence !== undefined
                  ? `${(insp.overall_confidence * 100).toFixed(0)}%`
                  : 'N/A';
                const violationCount = insp.violations?.length || 0;
                return (
                  <tr
                    key={insp.id}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                      transition: 'background 0.2s ease',
                      cursor: 'pointer',
                    }}
                    onClick={() => onSelectInspection(insp.id)}
                  >
                    <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>#{insp.id}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{insp.product_name || 'Unnamed Product'}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span className={`status-badge status-${insp.status}`} style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>
                        {insp.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{confPercent}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      {violationCount > 0 ? (
                        <span style={{ color: 'var(--error-color)', fontWeight: 600 }}>
                          {violationCount} {violationCount === 1 ? 'violation' : 'violations'}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>0</span>
                      )}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--text-muted)' }}>
                      {new Date(insp.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                      <button
                        className="btn"
                        style={{
                          padding: '0.25rem 0.6rem',
                          fontSize: '0.75rem',
                          background: 'rgba(59, 130, 246, 0.15)',
                          border: '1px solid var(--primary-color)',
                          color: 'var(--primary-color)',
                          boxShadow: 'none',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectInspection(insp.id);
                        }}
                      >
                        View Details →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 8: Product & Inspection History with Search & Status Filter */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem' }}>Product & Inspection History</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Search across historical packaging records and filter by regulatory outcome
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Search product name or notes..."
              value={historySearch}
              onChange={handleSearchChange}
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--glass-border)',
                borderRadius: '6px',
                padding: '0.45rem 0.8rem',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
                minWidth: '220px',
              }}
              data-testid="history-search-input"
            />

            <select
              value={historyStatus}
              onChange={handleStatusFilterChange}
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--glass-border)',
                borderRadius: '6px',
                padding: '0.45rem 0.8rem',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
                outline: 'none',
              }}
              data-testid="history-status-select"
            >
              <option value="ALL">All Statuses</option>
              <option value="COMPLIANT">Compliant</option>
              <option value="NON_COMPLIANT">Non-Compliant</option>
              <option value="MANUAL_REVIEW">Manual Review</option>
              <option value="CREATED">Created (Pending)</option>
            </select>
          </div>
        </div>

        {/* History Table */}
        <div style={{ overflowX: 'auto' }}>
          {historyLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Filtering records...
            </div>
          ) : historyList.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No inspections match your search/filter criteria.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }} data-testid="history-table">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--glass-border)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem' }}>ID</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Product Name</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Compliance Status</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Confidence</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Images</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>Created At</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {historyList.map((item) => (
                  <tr
                    key={item.id}
                    style={{
                      borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                      cursor: 'pointer',
                    }}
                    onClick={() => onSelectInspection(item.id)}
                  >
                    <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>#{item.id}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{item.product_name || '—'}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span className={`status-badge status-${item.status}`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.45rem' }}>
                        {item.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      {item.overall_confidence !== null && item.overall_confidence !== undefined
                        ? `${(item.overall_confidence * 100).toFixed(0)}%`
                        : '—'}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>{item.images?.length || 0}</td>
                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--text-muted)' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                      <button
                        className="btn"
                        style={{
                          padding: '0.2rem 0.5rem',
                          fontSize: '0.75rem',
                          background: 'transparent',
                          border: '1px solid var(--glass-border)',
                          color: 'var(--text-muted)',
                          boxShadow: 'none',
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectInspection(item.id);
                        }}
                      >
                        Open ↗
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardView;
