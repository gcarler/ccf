import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TestimonialForm from './TestimonialForm';
import { toast } from 'sonner';
import { createCmsPostByCategory } from '@/lib/cms/v2';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

vi.mock('@/lib/cms/v2', () => ({
  createCmsPostByCategory: vi.fn(),
}));

describe('TestimonialForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('triggers toast.error if token is missing on submit', async () => {
    render(<TestimonialForm token="" />);
    const textarea = screen.getByPlaceholderText(/Como ha sido tu proceso/i);
    fireEvent.change(textarea, { target: { value: 'Mi testimonio de fe.' } });

    const submitBtn = screen.getByRole('button', { name: /Publicar testimonio/i });
    fireEvent.click(submitBtn);

    expect(toast.error).toHaveBeenCalledWith('Inicia sesión para enviar un testimonio.');
  });

  it('triggers toast.success and resets form on successful submission', async () => {
    vi.mocked(createCmsPostByCategory).mockResolvedValueOnce({ id: '1', slug: 'test' } as unknown as Awaited<ReturnType<typeof createCmsPostByCategory>>);
    const onSubmittedMock = vi.fn();

    render(<TestimonialForm token="mock-token" onSubmitted={onSubmittedMock} />);

    const textarea = screen.getByPlaceholderText(/Como ha sido tu proceso/i);
    fireEvent.change(textarea, { target: { value: 'Mi testimonio de fe.' } });

    const submitBtn = screen.getByRole('button', { name: /Publicar testimonio/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createCmsPostByCategory).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith('Gracias. Tu testimonio fue enviado para moderación.');
      expect(onSubmittedMock).toHaveBeenCalled();
    });
  });

  it('triggers toast.error on submission failure', async () => {
    vi.mocked(createCmsPostByCategory).mockRejectedValueOnce(new Error('Network error'));

    render(<TestimonialForm token="mock-token" />);

    const textarea = screen.getByPlaceholderText(/Como ha sido tu proceso/i);
    fireEvent.change(textarea, { target: { value: 'Mi testimonio de fe.' } });

    const submitBtn = screen.getByRole('button', { name: /Publicar testimonio/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Hubo un error al enviar el testimonio.');
    });
  });
});
