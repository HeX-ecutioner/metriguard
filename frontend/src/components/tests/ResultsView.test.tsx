import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResultsView from '../ResultsView';
import { apiClient } from '../../api/client';
import type { Inspection } from '../../api/client';

describe('ResultsView PDF Reporting Action', () => {
  const baseInspection: Inspection = {
    id: 42,
    status: 'COMPLIANT',
    product_name: 'Organic Wheat Flour 1kg',
    overall_confidence: 0.94,
    notes: 'Clean scan',
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:01:00Z',
    images: [],
    declarations: [
      {
        id: 1,
        declaration_type: 'MRP',
        extracted_value: 'Rs. 95.00',
        confidence: 0.98,
      },
    ],
    violations: [],
    result: {
      final_status: 'COMPLIANT',
      summary: 'All declarations compliant.',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/mock-uuid');
    window.URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('renders "Generate PDF" button for a completed inspection', () => {
    render(<ResultsView inspection={baseInspection} />);

    const pdfBtn = screen.getByRole('button', { name: /generate pdf/i });
    expect(pdfBtn).toBeDefined();
    expect(pdfBtn.hasAttribute('disabled')).toBe(false);
  });

  it('does not render "Generate PDF" button for an incomplete inspection', () => {
    const incompleteInspection: Inspection = {
      ...baseInspection,
      status: 'PROCESSING',
    };
    render(<ResultsView inspection={incompleteInspection} />);

    expect(screen.queryByRole('button', { name: /generate pdf/i })).toBeNull();
  });

  it('handles successful PDF download and triggers browser save without altering inspection', async () => {
    const mockBlob = new Blob(['%PDF-1.4 mock pdf data'], { type: 'application/pdf' });
    const downloadSpy = vi.spyOn(apiClient, 'downloadInspectionReport').mockResolvedValue(mockBlob);

    render(<ResultsView inspection={baseInspection} />);

    const pdfBtn = screen.getByRole('button', { name: /generate pdf/i });
    fireEvent.click(pdfBtn);

    // Verify API called with exact inspection ID
    expect(downloadSpy).toHaveBeenCalledWith(42);

    await waitFor(() => {
      expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
      expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost/mock-uuid');
      // Button restored to normal state
      expect(screen.getByRole('button', { name: /generate pdf/i })).toBeDefined();
    });
  });

  it('shows loading state and prevents duplicate clicks while generating', async () => {
    let resolveDownload: (blob: Blob) => void = () => {};
    const downloadPromise = new Promise<Blob>((resolve) => {
      resolveDownload = resolve;
    });

    const downloadSpy = vi.spyOn(apiClient, 'downloadInspectionReport').mockReturnValue(downloadPromise);

    render(<ResultsView inspection={baseInspection} />);

    const pdfBtn = screen.getByRole('button', { name: /generate pdf/i });
    fireEvent.click(pdfBtn);

    // Rapid double click
    fireEvent.click(pdfBtn);

    // Only one download call should be initiated
    expect(downloadSpy).toHaveBeenCalledTimes(1);

    // Button should show loading state and be disabled
    expect(screen.getByRole('button', { name: /generating pdf/i })).toBeDefined();
    const loadingBtn = screen.getByRole('button', { name: /generating pdf/i });
    expect(loadingBtn.hasAttribute('disabled')).toBe(true);

    // Resolve download
    resolveDownload(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /generate pdf/i })).toBeDefined();
    });
  });

  it('displays clear error alert if PDF generation fails', async () => {
    vi.spyOn(apiClient, 'downloadInspectionReport').mockRejectedValue({
      detail: 'Inspection #42 is in status CREATED and has not completed yet.',
      status_code: 409,
    });

    render(<ResultsView inspection={baseInspection} />);

    const pdfBtn = screen.getByRole('button', { name: /generate pdf/i });
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(/Inspection #42 is in status CREATED and has not completed yet/i)).toBeDefined();
    });

    // Dismiss error
    const dismissBtn = screen.getByRole('button', { name: '×' });
    fireEvent.click(dismissBtn);

    expect(screen.queryByRole('alert')).toBeNull();
  });
});
