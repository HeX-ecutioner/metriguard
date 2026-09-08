import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import { apiClient } from '../api/client';
import type { Inspection, PackageImage } from '../api/client';

describe('Frontend End-to-End Consecutive Inspection Lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('completes the full lifecycle across two consecutive inspections with state separation', async () => {
    // 1. Mock inspections A and B
    const inspectionA: Inspection = {
      id: 101,
      status: 'COMPLIANT',
      product_name: 'Product Alpha 500g',
      overall_confidence: 0.95,
      notes: null,
      created_at: '2026-09-08T10:00:00Z',
      updated_at: '2026-09-08T10:01:00Z',
      images: [
        {
          id: 1,
          inspection_id: 101,
          file_path: 'uploads/alpha.jpg',
          original_filename: 'alpha.jpg',
          mime_type: 'image/jpeg',
          file_size: 20480,
          width: 800,
          height: 600,
          created_at: '2026-09-08T10:01:00Z',
        },
      ],
      declarations: [
        {
          id: 1,
          declaration_type: 'MRP',
          extracted_value: 'Rs. 150.00',
          confidence: 0.98,
        },
      ],
      violations: [],
      result: {
        final_status: 'COMPLIANT',
        summary: 'All declarations compliant.',
      },
    };

    const packageImageA: PackageImage = {
      id: 1,
      inspection_id: 101,
      file_path: 'uploads/alpha.jpg',
      original_filename: 'alpha.jpg',
      mime_type: 'image/jpeg',
      file_size: 20480,
      width: 800,
      height: 600,
      created_at: '2026-09-08T10:01:00Z',
    };

    const inspectionB: Inspection = {
      id: 102,
      status: 'NON_COMPLIANT',
      product_name: 'Product Beta 1kg',
      overall_confidence: 0.85,
      notes: null,
      created_at: '2026-09-08T11:00:00Z',
      updated_at: '2026-09-08T11:01:00Z',
      images: [
        {
          id: 2,
          inspection_id: 102,
          file_path: 'uploads/beta.jpg',
          original_filename: 'beta.jpg',
          mime_type: 'image/jpeg',
          file_size: 40960,
          width: 1024,
          height: 768,
          created_at: '2026-09-08T11:01:00Z',
        },
      ],
      declarations: [],
      violations: [
        {
          id: 10,
          rule_id: 'LMR-2011-R06-1-E',
          rule_version: '1.0.0',
          title: 'LMR-2011-R06-1-E',
          explanation: 'Mandatory MRP declaration is missing.',
          severity: 'CRITICAL',
          confidence: 0.95,
        },
      ],
      result: {
        final_status: 'NON_COMPLIANT',
        summary: '1 violation detected.',
      },
    };

    const packageImageB: PackageImage = {
      id: 2,
      inspection_id: 102,
      file_path: 'uploads/beta.jpg',
      original_filename: 'beta.jpg',
      mime_type: 'image/jpeg',
      file_size: 40960,
      width: 1024,
      height: 768,
      created_at: '2026-09-08T11:01:00Z',
    };

    // Configure spy handlers
    let createCallCount = 0;
    vi.spyOn(apiClient, 'createInspection').mockImplementation(async (payload) => {
      createCallCount++;
      if (createCallCount === 1) {
        return {
          id: 101,
          status: 'CREATED',
          product_name: payload?.product_name || null,
          overall_confidence: null,
          notes: null,
          created_at: '2026-09-08T10:00:00Z',
          updated_at: '2026-09-08T10:00:00Z',
          images: [],
        };
      } else {
        return {
          id: 102,
          status: 'CREATED',
          product_name: payload?.product_name || null,
          overall_confidence: null,
          notes: null,
          created_at: '2026-09-08T11:00:00Z',
          updated_at: '2026-09-08T11:00:00Z',
          images: [],
        };
      }
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockImplementation(async (inspectionId) => {
      if (inspectionId === 101) return packageImageA;
      return packageImageB;
    });

    vi.spyOn(apiClient, 'getInspection').mockImplementation(async (inspectionId) => {
      if (inspectionId === 101) return inspectionA;
      return inspectionB;
    });

    vi.spyOn(apiClient, 'getDashboardStats').mockResolvedValue({
      total_inspections: 0,
      compliant_inspections: 0,
      non_compliant_inspections: 0,
      manual_review_inspections: 0,
      top_violations: [],
      recent_inspections: [],
    });

    // Render Main Application
    render(<App />);

    // Navigate to "New Inspection" tab and wait for dropzone
    const newTab = screen.getByTestId('tab-new-inspection');
    fireEvent.click(newTab);

    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
    });

    // =========================================================================
    // STEP 1: Select Image A locally (zero network calls)
    // =========================================================================
    const fileA = new File(['alpha-bytes'], 'alpha.jpg', { type: 'image/jpeg' });
    const inputA = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(inputA, { target: { files: [fileA] } });

    await waitFor(() => {
      expect(screen.getByText(/alpha.jpg/i)).toBeDefined();
      expect(screen.getByRole('button', { name: /start inspection/i })).toBeDefined();
    }, { timeout: 3000 });

    // =========================================================================
    // STEP 2: Start Inspection A -> Inspection #101 completes
    // =========================================================================
    const startBtn = screen.getByRole('button', { name: /start inspection/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Inspection Report #\s*101/i })).toBeDefined();
      expect(screen.getByText(/^COMPLIANT$/i)).toBeDefined();
      expect(screen.getByText(/Rs. 150.00/i)).toBeDefined();
    }, { timeout: 3000 });

    // =========================================================================
    // STEP 3: Click "Upload another image" -> complete reset to IDLE
    // =========================================================================
    // Click from the ResultsView or ImageUpload
    const uploadAnotherBtn = screen.getAllByText(/\+ Upload Another Image/i)[0];
    fireEvent.click(uploadAnotherBtn);

    await waitFor(() => {
      // Dropzone is back in clean IDLE state
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
      // Report #101 is cleared
      expect(screen.queryByRole('heading', { level: 2, name: /Inspection Report #\s*101/i })).toBeNull();
      expect(screen.queryByText(/Rs. 150.00/i)).toBeNull();
    });

    // =========================================================================
    // STEP 4: Select Image B locally
    // =========================================================================
    const fileB = new File(['beta-bytes'], 'beta.jpg', { type: 'image/jpeg' });
    const inputB = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(inputB, { target: { files: [fileB] } });

    await waitFor(() => {
      expect(screen.getByText(/beta.jpg/i)).toBeDefined();
      expect(screen.getByRole('button', { name: /start inspection/i })).toBeDefined();
    }, { timeout: 3000 });

    // =========================================================================
    // STEP 5: Start Inspection B -> Inspection #102 completes
    // =========================================================================
    const startBtnB = screen.getByRole('button', { name: /start inspection/i });
    fireEvent.click(startBtnB);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Inspection Report #\s*102/i })).toBeDefined();
      expect(screen.getByText(/^NON COMPLIANT$/i)).toBeDefined();
      expect(screen.getByText(/Mandatory MRP declaration is missing/i)).toBeDefined();
    }, { timeout: 3000 });

    // =========================================================================
    // STEP 6: Invariant Verifications
    // =========================================================================
    // Inspection A and B have distinct IDs
    expect(inspectionA.id).not.toBe(inspectionB.id);
    // Inspection A's data is not present in Inspection B's report
    expect(screen.queryByRole('heading', { level: 2, name: /Inspection Report #\s*101/i })).toBeNull();
    expect(screen.queryByText(/Rs. 150.00/i)).toBeNull();
  });
});
