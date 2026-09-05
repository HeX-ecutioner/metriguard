import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ImageUpload from './ImageUpload';

describe('ImageUpload Component', () => {
  it('renders upload area correctly', () => {
    const handleUpload = vi.fn();
    render(<ImageUpload onUpload={handleUpload} isProcessing={false} />);

    expect(screen.getByText(/Upload Package Image/i)).toBeDefined();
    expect(screen.getByText(/Drag & Drop Image Here/i)).toBeDefined();
    expect(screen.getByText(/or click to browse/i)).toBeDefined();
  });
});
