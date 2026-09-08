import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ImageUpload from './ImageUpload';
import { apiClient } from '../api/client';
import type { PackageImage, Inspection } from '../api/client';

describe('ImageUpload Component Lifecycle & Invariants', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders STATE A: IDLE correctly with dropzone and instructions', () => {
    render(<ImageUpload />);

    expect(screen.getByText(/Upload Package Image/i)).toBeDefined();
    expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
    expect(screen.getByText(/Supported formats: JPEG, PNG, WebP/i)).toBeDefined();
    expect(screen.queryByText(/Start Inspection/i)).toBeNull();
    expect(screen.queryByText(/Cancel/i)).toBeNull();
  });

  it('transitions to STATE B: IMAGE_SELECTED on file selection without calling any backend APIs', async () => {
    const createSpy = vi.spyOn(apiClient, 'createInspection');
    const uploadSpy = vi.spyOn(apiClient, 'uploadInspectionImage');

    render(<ImageUpload />);

    const file = new File(['fake-jpeg-bytes'], 'test_package.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/test_package.jpg/i)).toBeDefined();
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
      expect(screen.getByText(/Cancel/i)).toBeDefined();
    });

    // Verify ZERO backend requests were made in IMAGE_SELECTED state
    expect(createSpy).not.toHaveBeenCalled();
    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it('cancels from STATE B back to STATE A: IDLE with zero server calls or side-effects', async () => {
    const createSpy = vi.spyOn(apiClient, 'createInspection');
    const uploadSpy = vi.spyOn(apiClient, 'uploadInspectionImage');

    render(<ImageUpload />);

    const file = new File(['fake-jpeg-bytes'], 'cancel_me.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    // Click Cancel in IMAGE_SELECTED state
    const cancelBtn = screen.getByText(/^Cancel$/i);
    fireEvent.click(cancelBtn);

    // Verify it returned to IDLE
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
      expect(screen.queryByText(/cancel_me.jpg/i)).toBeNull();
      expect(screen.queryByText(/Start Inspection/i)).toBeNull();
    });

    // Zero backend calls made
    expect(createSpy).not.toHaveBeenCalled();
    expect(uploadSpy).not.toHaveBeenCalled();
  });

  it('transitions STATE B -> C -> D: Starts inspection, creates session, uploads image, and displays completed status', async () => {
    vi.spyOn(apiClient, 'createInspection').mockResolvedValue({
      id: 77,
      status: 'CREATED',
      product_name: 'Premium Salt 1kg',
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [],
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockResolvedValue({
      id: 101,
      inspection_id: 77,
      file_path: 'uploads/salt.jpg',
      original_filename: 'salt.jpg',
      mime_type: 'image/jpeg',
      file_size: 102400,
      width: 800,
      height: 600,
      created_at: '2026-09-06T10:01:00Z',
    });

    vi.spyOn(apiClient, 'getInspection').mockResolvedValue({
      id: 77,
      status: 'COMPLIANT',
      product_name: 'Premium Salt 1kg',
      overall_confidence: 0.95,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:01:00Z',
      images: [
        {
          id: 101,
          inspection_id: 77,
          file_path: 'uploads/salt.jpg',
          original_filename: 'salt.jpg',
          mime_type: 'image/jpeg',
          file_size: 102400,
          width: 800,
          height: 600,
          created_at: '2026-09-06T10:01:00Z',
        },
      ],
    });

    const handleSuccess = vi.fn();
    render(<ImageUpload onUploadSuccess={handleSuccess} />);

    const file = new File(['fake-jpeg-bytes'], 'salt.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    // Click Start Inspection
    fireEvent.click(screen.getByText(/Start Inspection/i));

    // Verify completed status and upload another image button
    await waitFor(() => {
      expect(screen.getByText(/Inspection Completed Successfully/i)).toBeDefined();
      expect(screen.getByText(/Inspection ID: #77/i)).toBeDefined();
      expect(screen.getByText(/\+ Upload Another Image/i)).toBeDefined();
      expect(handleSuccess).toHaveBeenCalledTimes(1);
    });
  });

  it('handles STATE E: UPLOAD_ANOTHER_IMAGE by resetting all local state and notifying parent', async () => {
    vi.spyOn(apiClient, 'createInspection').mockResolvedValue({
      id: 88,
      status: 'CREATED',
      product_name: null,
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [],
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockResolvedValue({
      id: 202,
      inspection_id: 88,
      file_path: 'uploads/first.jpg',
      original_filename: 'first.jpg',
      mime_type: 'image/jpeg',
      file_size: 51200,
      width: 640,
      height: 480,
      created_at: '2026-09-06T10:01:00Z',
    });

    vi.spyOn(apiClient, 'getInspection').mockResolvedValue({
      id: 88,
      status: 'COMPLIANT',
      product_name: null,
      overall_confidence: 0.9,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:01:00Z',
      images: [
        {
          id: 202,
          inspection_id: 88,
          file_path: 'uploads/first.jpg',
          original_filename: 'first.jpg',
          mime_type: 'image/jpeg',
          file_size: 51200,
          width: 640,
          height: 480,
          created_at: '2026-09-06T10:01:00Z',
        },
      ],
    });

    const handleAnotherImage = vi.fn();
    render(<ImageUpload onUploadAnotherImage={handleAnotherImage} />);

    // Select and start inspection
    const file = new File(['fake-bytes'], 'first.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    fireEvent.click(screen.getByText(/Start Inspection/i));

    await waitFor(() => {
      expect(screen.getByText(/\+ Upload Another Image/i)).toBeDefined();
    });

    // Click Upload Another Image
    fireEvent.click(screen.getByText(/\+ Upload Another Image/i));

    // Verify complete reset to IDLE and parent notification
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
      expect(screen.queryByText(/first\.jpg/i)).toBeNull();
      expect(screen.queryByText(/Inspection ID: #88/i)).toBeNull();
      expect(handleAnotherImage).toHaveBeenCalledTimes(1);
    });
  });

  it('stale response protection: abandons in-flight response if cancelled', async () => {
    let resolveUpload: (val: PackageImage) => void = () => {};
    const uploadPromise = new Promise<PackageImage>((resolve) => {
      resolveUpload = resolve;
    });

    vi.spyOn(apiClient, 'createInspection').mockResolvedValue({
      id: 99,
      status: 'CREATED',
      product_name: null,
      overall_confidence: null,
      notes: null,
      created_at: '2026-09-06T10:00:00Z',
      updated_at: '2026-09-06T10:00:00Z',
      images: [],
    });

    vi.spyOn(apiClient, 'uploadInspectionImage').mockReturnValue(uploadPromise);

    const handleSuccess = vi.fn();
    render(<ImageUpload onUploadSuccess={handleSuccess} />);

    const file = new File(['fake-bytes'], 'in_flight.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    fireEvent.click(screen.getByText(/Start Inspection/i));

    await waitFor(() => {
      expect(screen.getByText(/Return to upload screen/i)).toBeDefined();
    });

    // User abandons / cancels the in-flight processing
    fireEvent.click(screen.getByText(/Return to upload screen/i));

    // Late network response arrives
    resolveUpload({
      id: 999,
      inspection_id: 99,
      file_path: 'uploads/late.jpg',
      original_filename: 'late.jpg',
      mime_type: 'image/jpeg',
      file_size: 1000,
      width: 100,
      height: 100,
      created_at: '2026-09-06T10:02:00Z',
    });

    // Verify stale response did NOT trigger success callback or pollute UI
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
      expect(handleSuccess).not.toHaveBeenCalled();
    });
  });

  it('double-click protection: rapidly clicking Start Inspection creates only one session', async () => {
    let resolveCreate: (val: Inspection) => void = () => {};
    const createPromise = new Promise<Inspection>((resolve) => {
      resolveCreate = resolve;
    });

    const createSpy = vi.spyOn(apiClient, 'createInspection').mockReturnValue(createPromise);
    const uploadSpy = vi.spyOn(apiClient, 'uploadInspectionImage').mockResolvedValue({
      id: 501,
      inspection_id: 123,
      file_path: 'uploads/double.jpg',
      original_filename: 'double.jpg',
      mime_type: 'image/jpeg',
      file_size: 1000,
      width: 100,
      height: 100,
      created_at: '2026-09-08T12:00:00Z',
    });

    render(<ImageUpload />);

    const file = new File(['fake-bytes'], 'double.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    const startBtn = screen.getByText(/Start Inspection/i);

    // Rapidly click twice
    fireEvent.click(startBtn);
    fireEvent.click(startBtn);

    // Only one createInspection call should be initiated
    expect(createSpy).toHaveBeenCalledTimes(1);

    // Resolve the promise
    await act(async () => {
      resolveCreate({
        id: 123,
        status: 'CREATED',
        product_name: null,
        overall_confidence: null,
        notes: null,
        created_at: '2026-09-08T12:00:00Z',
        updated_at: '2026-09-08T12:00:00Z',
        images: [],
      });
    });

    await waitFor(() => {
      expect(uploadSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('error state: displays error detail with Retry and Cancel options', async () => {
    vi.spyOn(apiClient, 'createInspection').mockRejectedValue({
      detail: 'Inspection session limit reached.',
      status_code: 429,
    });

    render(<ImageUpload />);

    const file = new File(['fake-bytes'], 'fail.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Start Inspection/i)).toBeDefined();
    });

    fireEvent.click(screen.getByText(/Start Inspection/i));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(/Inspection session limit reached/i)).toBeDefined();
      expect(screen.getByText(/Retry Inspection/i)).toBeDefined();
      expect(screen.getByText(/^Cancel$/i)).toBeDefined();
    });

    // Clicking Cancel returns to IDLE
    fireEvent.click(screen.getByText(/^Cancel$/i));
    await waitFor(() => {
      expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
    });
  });
});

