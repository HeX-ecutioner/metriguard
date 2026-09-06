import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ImageUpload from './ImageUpload';
import { apiClient } from '../api/client';

describe('ImageUpload Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders upload area and instructions correctly', () => {
    render(<ImageUpload />);

    expect(screen.getByText(/Upload Package Image/i)).toBeDefined();
    expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
    expect(screen.getByText(/Supported formats: JPEG, PNG, WebP/i)).toBeDefined();
  });

  it('handles frontend upload success flow and displays inspection ID and image metadata', async () => {
    // Mock API client methods
    vi.spyOn(apiClient, 'createInspection').mockResolvedValue({
      id: 42,
      status: 'CREATED',
      product_name: 'Test Salt 1kg',
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [],
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockResolvedValue({
      id: 101,
      inspection_id: 42,
      file_path: 'uploads/abc123_salt.jpg',
      original_filename: 'salt.jpg',
      mime_type: 'image/jpeg',
      file_size: 204800,
      width: 1200,
      height: 900,
      created_at: '2026-09-06T10:01:00Z',
    });

    vi.spyOn(apiClient, 'getInspection').mockResolvedValue({
      id: 42,
      status: 'CREATED',
      product_name: 'Test Salt 1kg',
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:01:00Z',
      images: [
        {
          id: 101,
          inspection_id: 42,
          file_path: 'uploads/abc123_salt.jpg',
          original_filename: 'salt.jpg',
          mime_type: 'image/jpeg',
          file_size: 204800,
          width: 1200,
          height: 900,
          created_at: '2026-09-06T10:01:00Z',
        },
      ],
    });

    const handleSuccess = vi.fn();
    render(<ImageUpload onUploadSuccess={handleSuccess} />);

    // Simulate selecting a file
    const file = new File(['fake-jpeg-binary-data'], 'salt.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    // Verify preview state appeared with Upload button
    await waitFor(() => {
      expect(screen.getByText(/Upload Image/i)).toBeDefined();
    });

    // Click Upload Image
    const uploadBtn = screen.getByText(/Upload Image/i);
    fireEvent.click(uploadBtn);

    // Verify successful upload display
    await waitFor(() => {
      expect(screen.getByText(/Image Uploaded Successfully/i)).toBeDefined();
      expect(screen.getByText(/Inspection ID: #42/i)).toBeDefined();
      expect(screen.getByText(/1200 × 900 px/i)).toBeDefined();
      expect(handleSuccess).toHaveBeenCalledTimes(1);
    });
  });

  it('handles frontend upload failure and displays validation error from API', async () => {
    vi.spyOn(apiClient, 'createInspection').mockResolvedValue({
      id: 55,
      status: 'CREATED',
      product_name: null,
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [],
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockRejectedValue({
      detail: "Unsupported file extension '.exe'. Allowed extensions are: .jpg, .jpeg, .png, .webp.",
      error_code: 'INVALID_EXTENSION',
      status_code: 400,
    });

    render(<ImageUpload />);

    // Simulate selecting a file
    const file = new File(['fake-binary'], 'evil.exe', { type: 'application/x-msdownload' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Upload Image/i)).toBeDefined();
    });

    // Click Upload Image
    const uploadBtn = screen.getByText(/Upload Image/i);
    fireEvent.click(uploadBtn);

    // Verify validation error is displayed and no fake success
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(/Unsupported file extension '\.exe'/i)).toBeDefined();
      expect(screen.queryByText(/Image Uploaded Successfully/i)).toBeNull();
    });
  });
});
