import React, { useState, useEffect, useCallback } from 'react';
import type { DashboardStats, Inspection } from '../api/client';
import { apiClient } from '../api/client';
import './styles/DashboardView.css';

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

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    apiClient
      .getDashboardStats()
      .then((data) => {
        setStats(data);
        setHistoryList(data.recent_inspections || []);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const apiErr = err as { detail?: string };
        setError(apiErr?.detail || 'Failed to connect to backend inspection service.');
        setLoading(false);
      });
  };

  useEffect(() => {
    let cancelled = false;
    apiClient
      .getDashboardStats()
      .then((data) => {
        if (!cancelled) {
          setStats(data);
          setHistoryList(data.recent_inspections || []);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const apiErr = err as { detail?: string };
          setError(apiErr?.detail || 'Failed to connect to backend inspection service.');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
        className="glass-card fade-in dashboard-loading-card"
        data-testid="dashboard-loading"
      >
        <div className="spinner" />
        <h3 className="dashboard-loading-title">Loading MetriGuard Dashboard...</h3>
        <p className="dashboard-loading-text">
          Retrieving live compliance statistics and inspection records from database.
        </p>
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div
        className="glass-card fade-in dashboard-error-card"
        data-testid="dashboard-error"
      >
        <div className="dashboard-error-icon">⚠️</div>
        <h3 className="dashboard-error-title">Failed to Load Dashboard</h3>
        <p className="dashboard-error-message">
          {error}
        </p>
        <button className="btn dashboard-retry-btn" onClick={handleRetry}>
          🔄 Retry Connection
        </button>
      </div>
    );
  }

  // 3. Empty State
  if (!stats || stats.total_inspections === 0) {
    return (
      <div
        className="glass-card fade-in dashboard-empty-card"
        data-testid="dashboard-empty"
      >
        <div className="dashboard-empty-icon">📦</div>
        <h3 className="dashboard-empty-title">No Inspections Recorded Yet</h3>
        <p className="dashboard-empty-text">
          The database currently contains no packaged commodity inspections. Upload a package label image to begin automated Legal Metrology compliance verification.
        </p>
        <button className="btn dashboard-empty-btn" onClick={onNewInspection}>
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
    <div className="fade-in dashboard-container" data-testid="dashboard-content">
      {/* 1-4. Stat Cards Grid */}
      <div
        className="dashboard-metrics-grid"
        data-testid="metric-cards"
      >
        {/* Card 1: Total Inspections */}
        <div className="glass-card dashboard-metric-card metric-primary">
          <span className="dashboard-metric-label">
            Total Inspections
          </span>
          <div className="dashboard-metric-value">
            {stats.total_inspections}
          </div>
          <span className="dashboard-metric-subtext">All evaluated packages</span>
        </div>

        {/* Card 2: Compliant */}
        <div className="glass-card dashboard-metric-card metric-success">
          <span className="dashboard-metric-label">
            Compliant
          </span>
          <div className="dashboard-metric-value val-success">
            {stats.compliant_inspections}
          </div>
          <span className="dashboard-metric-subtext">
            {stats.total_inspections > 0
              ? `${((stats.compliant_inspections / stats.total_inspections) * 100).toFixed(1)}% of total`
              : '0%'}
          </span>
        </div>

        {/* Card 3: Non-Compliant */}
        <div className="glass-card dashboard-metric-card metric-error">
          <span className="dashboard-metric-label">
            Non-Compliant
          </span>
          <div className="dashboard-metric-value val-error">
            {stats.non_compliant_inspections}
          </div>
          <span className="dashboard-metric-subtext">
            {stats.total_inspections > 0
              ? `${((stats.non_compliant_inspections / stats.total_inspections) * 100).toFixed(1)}% violations`
              : '0%'}
          </span>
        </div>

        {/* Card 4: Manual Review */}
        <div className="glass-card dashboard-metric-card metric-warning">
          <span className="dashboard-metric-label">
            Manual Review
          </span>
          <div className="dashboard-metric-value val-warning">
            {stats.manual_review_inspections}
          </div>
          <span className="dashboard-metric-subtext">Requires officer review</span>
        </div>
      </div>

      {/* Mid-Row: Top Violation Types & Quick Actions */}
      <div className="dashboard-mid-row">
        {/* Section 6: Top Violation Types */}
        <div className="glass-card dashboard-violations-card">
          <div className="dashboard-section-header">
            <h3 className="dashboard-section-title">Top Regulatory Violation Types</h3>
            <span className="dashboard-section-subtitle">LMR 2011 Enforcements</span>
          </div>

          {stats.top_violations.length === 0 ? (
            <p className="dashboard-violations-empty">
              No violations recorded in the database.
            </p>
          ) : (
            <div className="dashboard-violations-list" data-testid="top-violations-list">
              {stats.top_violations.map((violation) => {
                const percent = Math.round((violation.count / maxViolationCount) * 100);
                return (
                  <div key={violation.rule_id} className="dashboard-violation-item">
                    <div className="dashboard-violation-header">
                      <span className="dashboard-violation-rule">
                        {violation.rule_id}
                        <span className="dashboard-violation-rule-title">
                          ({violation.title})
                        </span>
                      </span>
                      <div className="dashboard-violation-count-wrap">
                        <span
                          className={`dashboard-violation-severity ${
                            violation.severity === 'CRITICAL' ? 'severity-critical' : 'severity-warning'
                          }`}
                        >
                          {violation.severity}
                        </span>
                        <strong className="dashboard-violation-count">{violation.count}</strong>
                      </div>
                    </div>
                    {/* CSS Progress Meter Bar */}
                    <div className="dashboard-meter-track">
                      <div
                        className="dashboard-meter-fill"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Action / Pipeline Quick Card */}
        <div className="glass-card dashboard-quick-action-card">
          <div>
            <h3 className="dashboard-quick-action-title">New Package Inspection</h3>
            <p className="dashboard-quick-action-desc">
              Run automated Legal Metrology (2011) compliance verification on a new packaged commodity label.
            </p>
            <ul className="dashboard-quick-action-list">
              <li>✓ OCR detection of declarations & units</li>
              <li>✓ Deterministic verification across 6 active rules</li>
              <li>✓ Traceable evidence bounding boxes & image links</li>
            </ul>
          </div>

          <button className="btn dashboard-action-btn" onClick={onNewInspection}>
            ⚡ Launch Inspection Session
          </button>
        </div>
      </div>

      {/* Section 5: Recent Inspections Table */}
      <div className="glass-card dashboard-table-card">
        <div className="dashboard-table-header">
          <div>
            <h3 className="dashboard-section-title">Recent Inspections</h3>
            <p className="dashboard-section-subtitle">
              Latest 10 package inspection runs stored in database
            </p>
          </div>
        </div>

        <div className="dashboard-table-wrapper">
          <table className="dashboard-table" data-testid="recent-inspections-table">
            <thead>
              <tr className="dashboard-table-head-row">
                <th className="dashboard-th">ID</th>
                <th className="dashboard-th">Product / Commodity</th>
                <th className="dashboard-th">Status</th>
                <th className="dashboard-th">Confidence</th>
                <th className="dashboard-th">Violations</th>
                <th className="dashboard-th">Date</th>
                <th className="dashboard-th dashboard-th-right">Action</th>
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
                    className="dashboard-tr"
                    onClick={() => onSelectInspection(insp.id)}
                  >
                    <td className="dashboard-td dashboard-td-bold">#{insp.id}</td>
                    <td className="dashboard-td">{insp.product_name || 'Unnamed Product'}</td>
                    <td className="dashboard-td">
                      <span className={`status-badge status-${insp.status} dashboard-status-badge`}>
                        {insp.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="dashboard-td">{confPercent}</td>
                    <td className="dashboard-td">
                      {violationCount > 0 ? (
                        <span className="dashboard-violation-badge">
                          {violationCount} {violationCount === 1 ? 'violation' : 'violations'}
                        </span>
                      ) : (
                        <span className="dashboard-td-muted">0</span>
                      )}
                    </td>
                    <td className="dashboard-td dashboard-td-muted">
                      {new Date(insp.created_at).toLocaleDateString()}
                    </td>
                    <td className="dashboard-td dashboard-td-right">
                      <button
                        className="btn dashboard-view-btn"
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
      <div className="glass-card dashboard-table-card">
        <div className="dashboard-header-filter-row">
          <div>
            <h3 className="dashboard-section-title">Product & Inspection History</h3>
            <p className="dashboard-section-subtitle">
              Search across historical packaging records and filter by regulatory outcome
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div className="dashboard-filter-controls">
            <input
              type="text"
              placeholder="Search product name or notes..."
              value={historySearch}
              onChange={handleSearchChange}
              className="dashboard-search-input"
              data-testid="history-search-input"
            />

            <select
              value={historyStatus}
              onChange={handleStatusFilterChange}
              className="dashboard-select"
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
        <div className="dashboard-table-wrapper">
          {historyLoading ? (
            <div className="dashboard-table-message">
              Filtering records...
            </div>
          ) : historyList.length === 0 ? (
            <div className="dashboard-table-message">
              No inspections match your search/filter criteria.
            </div>
          ) : (
            <table className="dashboard-table" data-testid="history-table">
              <thead>
                <tr className="dashboard-table-head-row">
                  <th className="dashboard-th">ID</th>
                  <th className="dashboard-th">Product Name</th>
                  <th className="dashboard-th">Compliance Status</th>
                  <th className="dashboard-th">Confidence</th>
                  <th className="dashboard-th">Images</th>
                  <th className="dashboard-th">Created At</th>
                  <th className="dashboard-th dashboard-th-right">Details</th>
                </tr>
              </thead>
              <tbody>
                {historyList.map((item) => (
                  <tr
                    key={item.id}
                    className="dashboard-tr"
                    onClick={() => onSelectInspection(item.id)}
                  >
                    <td className="dashboard-td dashboard-td-bold">#{item.id}</td>
                    <td className="dashboard-td">{item.product_name || '—'}</td>
                    <td className="dashboard-td">
                      <span className={`status-badge status-${item.status} dashboard-status-badge-small`}>
                        {item.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="dashboard-td">
                      {item.overall_confidence !== null && item.overall_confidence !== undefined
                        ? `${(item.overall_confidence * 100).toFixed(0)}%`
                        : '—'}
                    </td>
                    <td className="dashboard-td">{item.images?.length || 0}</td>
                    <td className="dashboard-td dashboard-td-muted">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="dashboard-td dashboard-td-right">
                      <button
                        className="btn dashboard-open-btn"
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
