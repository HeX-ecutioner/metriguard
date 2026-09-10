import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within, act } from '@testing-library/react';

import DashboardView from '../DashboardView';
import InspectionDetailView from '../InspectionDetailView';
import { apiClient } from '../../api/client';
import type { DashboardStats, Inspection } from '../../api/client';

const mockPopulatedStats: DashboardStats = {
  total_inspections: 12,
  compliant_inspections: 7,
  non_compliant_inspections: 3,
  manual_review_inspections: 2,
  top_violations: [
    {
      rule_id: 'LMR-2011-R06-MRP-01',
      title: 'MRP Declaration Missing',
      severity: 'CRITICAL',
      count: 3,
    },
    {
      rule_id: 'LMR-2011-R06-NETQTY-01',
      title: 'Net Quantity Missing',
      severity: 'ERROR',
      count: 2,
    },
  ],
  recent_inspections: [
    {
      id: 101,
      status: 'COMPLIANT',
      product_name: 'Organic Wheat Flour 5kg',
      overall_confidence: 0.965,
      notes: 'Supermarket audit',
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [
        {
          id: 1,
          inspection_id: 101,
          file_path: 'flour.jpg',
          original_filename: 'flour.jpg',
          mime_type: 'image/jpeg',
          file_size: 102400,
          width: 800,
          height: 600,
          created_at: '2026-09-06T10:00:00Z',
        },
      ],
      declarations: [
        {
          id: 501,
          declaration_type: 'MRP',
          extracted_value: 'Rs. 250.00',
          confidence: 0.98,
        },
        {
          id: 502,
          declaration_type: 'NET_QUANTITY',
          extracted_value: '5 kg',
          confidence: 0.95,
        },
      ],
      violations: [],
      result: {
        final_status: 'COMPLIANT',
        summary: 'All 6 Legal Metrology declarations verified successfully.',
      },
    },
    {
      id: 102,
      status: 'NON_COMPLIANT',
      product_name: 'Chocolate Biscuit 200g',
      overall_confidence: 0.88,
      notes: null,
      created_at: '2026-09-06T11:00:00Z',
      updated_at: '2026-09-06T11:00:00Z',
      images: [],
      declarations: [],
      violations: [
        {
          id: 601,
          rule_id: 'LMR-2011-R06-MRP-01',
          rule_version: '1.0.0',
          title: 'MRP Missing',
          explanation: 'No retail price found on principal display panel',
          severity: 'CRITICAL',
          confidence: 0.92,
        },
      ],
      result: {
        final_status: 'NON_COMPLIANT',
        summary: '1 critical violation found.',
      },
    },
  ],
};

const mockDetailInspection: Inspection = {
  id: 101,
  status: 'COMPLIANT',
  product_name: 'Organic Wheat Flour 5kg',
  overall_confidence: 0.965,
  notes: 'Audit passed cleanly',
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  images: [
    {
      id: 1,
      inspection_id: 101,
      file_path: 'flour.jpg',
      original_filename: 'flour.jpg',
      mime_type: 'image/jpeg',
      file_size: 102400,
      width: 800,
      height: 600,
      created_at: '2026-09-06T10:00:00Z',
    },
  ],
  declarations: [
    {
      id: 501,
      declaration_type: 'MRP',
      extracted_value: 'Rs. 250.00',
      confidence: 0.98,
      bounding_box: '{"x": 10, "y": 20, "width": 100, "height": 30}',
    },
    {
      id: 502,
      declaration_type: 'NET_QUANTITY',
      extracted_value: '5 kg',
      confidence: 0.95,
      bounding_box: null,
    },
  ],
  violations: [],
  result: {
    final_status: 'COMPLIANT',
    summary: 'All 6 Legal Metrology rules satisfied.',
  },
};

describe('MetriGuard Dashboard Component Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test 1: Loading state
  it('renders loading state indicator when dashboard data is fetching', () => {
    // Return an unresolved promise to keep component in loading state
    vi.spyOn(apiClient, 'getDashboardStats').mockReturnValue(new Promise(() => {}));

    render(
      <DashboardView
        onSelectInspection={vi.fn()}
        onNewInspection={vi.fn()}
      />
    );

    expect(screen.getByTestId('dashboard-loading')).toBeDefined();
    expect(screen.getByText(/Loading MetriGuard Dashboard.../i)).toBeDefined();
    expect(screen.getByText(/Retrieving live compliance statistics/i)).toBeDefined();
  });

  // Test 2: Empty state
  it('renders empty state with call-to-action when total inspections is 0', async () => {
    vi.spyOn(apiClient, 'getDashboardStats').mockResolvedValue({
      total_inspections: 0,
      compliant_inspections: 0,
      non_compliant_inspections: 0,
      manual_review_inspections: 0,
      top_violations: [],
      recent_inspections: [],
    });

    const onNewInspection = vi.fn();

    render(
      <DashboardView
        onSelectInspection={vi.fn()}
        onNewInspection={onNewInspection}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-empty')).toBeDefined();
    });

    expect(screen.getByText(/No Inspections Recorded Yet/i)).toBeDefined();
    expect(screen.getByText(/The database currently contains no packaged commodity inspections/i)).toBeDefined();

    const ctaBtn = screen.getByText(/⚡ Start First Inspection/i);
    expect(ctaBtn).toBeDefined();

    fireEvent.click(ctaBtn);
    expect(onNewInspection).toHaveBeenCalledTimes(1);
  });

  // Test 3: Populated dashboard
  it('renders populated dashboard with real counts, top violations, and recent inspections', async () => {
    vi.spyOn(apiClient, 'getDashboardStats').mockResolvedValue(mockPopulatedStats);

    const onSelectInspection = vi.fn();

    render(
      <DashboardView
        onSelectInspection={onSelectInspection}
        onNewInspection={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-content')).toBeDefined();
    });

    // 1-4. Stat Cards
    const metricCards = screen.getByTestId('metric-cards');
    expect(within(metricCards).getByText('12')).toBeDefined(); // Total
    expect(within(metricCards).getByText('7')).toBeDefined();  // Compliant
    expect(within(metricCards).getByText('3')).toBeDefined();  // Non-compliant
    expect(within(metricCards).getByText('2')).toBeDefined();  // Manual review


    // 6. Top violations
    expect(screen.getByText(/Top Regulatory Violation Types/i)).toBeDefined();
    expect(screen.getByText(/LMR-2011-R06-MRP-01/i)).toBeDefined();
    expect(screen.getByText(/LMR-2011-R06-NETQTY-01/i)).toBeDefined();

    // 5. Recent inspections table
    const recentTable = screen.getByTestId('recent-inspections-table');
    expect(within(recentTable).getByText(/Organic Wheat Flour 5kg/i)).toBeDefined();
    expect(within(recentTable).getByText(/Chocolate Biscuit 200g/i)).toBeDefined();

    // 8. Product history table
    const historyTable = screen.getByTestId('history-table');
    expect(within(historyTable).getByText(/Organic Wheat Flour 5kg/i)).toBeDefined();


    // Test clicking an inspection row triggers detail navigation
    const viewBtn = screen.getAllByText(/View Details →/i)[0];
    fireEvent.click(viewBtn);
    expect(onSelectInspection).toHaveBeenCalledWith(101);
  });

  // Test 4: API failure
  it('renders error state with retry button when backend API call fails', async () => {
    const errorSpy = vi.spyOn(apiClient, 'getDashboardStats').mockRejectedValue({
      detail: 'Network connection refused on port 8000',
      status_code: 503,
    });

    render(
      <DashboardView
        onSelectInspection={vi.fn()}
        onNewInspection={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-error')).toBeDefined();
    });

    expect(screen.getByText(/Failed to Load Dashboard/i)).toBeDefined();
    expect(screen.getByText(/Network connection refused on port 8000/i)).toBeDefined();

    const retryBtn = screen.getByText(/🔄 Retry Connection/i);
    expect(retryBtn).toBeDefined();

    // Test retry button
    await act(async () => {
      fireEvent.click(retryBtn);
    });
    expect(errorSpy).toHaveBeenCalledTimes(2);
  });


  // Test 5: Inspection detail rendering
  it('renders inspection detail page with declarations, violations, and back navigation', async () => {
    const onBackMock = vi.fn();

    render(
      <InspectionDetailView
        inspectionId={101}
        initialInspection={mockDetailInspection}
        onBack={onBackMock}
      />
    );

    // Header & Status
    expect(screen.getByText(/Inspection Report #101/i)).toBeDefined();
    expect(screen.getByText(/Organic Wheat Flour 5kg/i)).toBeDefined();
    expect(screen.getAllByText(/COMPLIANT/i).length).toBeGreaterThanOrEqual(1);


    // Confidence indicator
    expect(screen.getByText('96.5%')).toBeDefined();

    // Extracted declarations
    expect(screen.getByText(/Maximum Retail Price \(MRP\)/i)).toBeDefined();
    expect(screen.getByText(/Rs. 250.00/i)).toBeDefined();
    expect(screen.getByText(/Net Quantity/i)).toBeDefined();
    expect(screen.getByText(/5 kg/i)).toBeDefined();

    // Result summary
    expect(screen.getByText(/All 6 Legal Metrology rules satisfied./i)).toBeDefined();

    // Back to dashboard button
    const backBtn = screen.getByText(/← Back to Dashboard/i);
    expect(backBtn).toBeDefined();
    fireEvent.click(backBtn);
    expect(onBackMock).toHaveBeenCalledTimes(1);
  });
});
