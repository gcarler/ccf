/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CmsImageEditorModal from '@/components/cms/CmsImageEditorModal';
import { apiFetch } from '@/lib/http';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn(),
}));

// Mock Image & HTMLCanvasElement for JSDOM
beforeEach(() => {
    vi.clearAllMocks();

    globalThis.Image = class extends EventTarget {
        _src = '';
        onload: () => void = () => {};
        onerror: () => void = () => {};
        width = 800;
        height = 600;
        crossOrigin = '';

        get src() {
            return this._src;
        }
        set src(v: string) {
            this._src = v;
            setTimeout(() => {
                if (this.onload) this.onload();
            }, 0);
        }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;

    HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
        save: vi.fn(),
        restore: vi.fn(),
        clearRect: vi.fn(),
        translate: vi.fn(),
        rotate: vi.fn(),
        scale: vi.fn(),
        drawImage: vi.fn(),
        filter: '',
    });

    HTMLCanvasElement.prototype.toBlob = vi.fn().mockImplementation((callback, type) => {
        const dummyBlob = new Blob(['dummy content'], { type: type || 'image/png' });
        callback(dummyBlob);
    });
});

describe('CmsImageEditorModal', () => {
    const mockItem = {
        id: 'media-uuid-123',
        url: 'https://example.com/banner.png',
        filename: 'banner.png',
        mime_type: 'image/png',
        alt_text: 'Hero Banner',
        section: 'hero',
    };

    it('renders editing controls correctly', async () => {
        render(
            <CmsImageEditorModal
                item={mockItem}
                token="fake-token"
                onClose={vi.fn()}
                onSaveSuccess={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.getByText(/Editor de Imagen:/i)).toBeInTheDocument();
        });

        expect(screen.getByText('banner.png')).toBeInTheDocument();
        expect(screen.getByText(/Recorte \(Crop\)/i)).toBeInTheDocument();
        expect(screen.getByText(/Rotación/i)).toBeInTheDocument();
        expect(screen.getByText(/Brillo \/ Contraste/i)).toBeInTheDocument();
        expect(screen.getByText(/Voltear \(Flip\)/i)).toBeInTheDocument();

        expect(screen.getByRole('button', { name: /-90°/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /\+90°/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Horizontal/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Vertical/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Activar Recorte/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Guardar Cambios/i })).toBeInTheDocument();
    });

    it('toggles crop mode overlay when clicking crop button', async () => {
        render(
            <CmsImageEditorModal
                item={mockItem}
                token="fake-token"
                onClose={vi.fn()}
                onSaveSuccess={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Activar Recorte/i })).toBeInTheDocument();
        });

        const cropButton = screen.getByRole('button', { name: /Activar Recorte/i });
        fireEvent.click(cropButton);

        expect(screen.getByText('Desactivar Recorte')).toBeInTheDocument();
        expect(screen.getByText('Modo Recorte Activo')).toBeInTheDocument();
    });

    it('submits edited image blob to POST /cms/media/{id}/edit on Save', async () => {
        const mockNewItem = {
            id: 'media-uuid-456',
            url: 'https://example.com/banner_edited.png',
            filename: 'banner_edited.png',
        };
        vi.mocked(apiFetch).mockResolvedValueOnce(mockNewItem);

        const onSaveSuccessMock = vi.fn();
        const onCloseMock = vi.fn();

        render(
            <CmsImageEditorModal
                item={mockItem}
                token="fake-token"
                onClose={onCloseMock}
                onSaveSuccess={onSaveSuccessMock}
            />
        );

        await waitFor(() => {
            expect(screen.getByRole('button', { name: /Guardar Cambios/i })).not.toBeDisabled();
        });

        // Click rotation and flip buttons to test adjustments state
        fireEvent.click(screen.getByRole('button', { name: /\+90°/i }));
        fireEvent.click(screen.getByRole('button', { name: /Horizontal/i }));

        const saveButton = screen.getByRole('button', { name: /Guardar Cambios/i });
        fireEvent.click(saveButton);

        await waitFor(() => {
            expect(apiFetch).toHaveBeenCalledWith(
                `/cms/media/${mockItem.id}/edit`,
                expect.objectContaining({
                    method: 'POST',
                    token: 'fake-token',
                    body: expect.any(FormData),
                })
            );
            expect(onSaveSuccessMock).toHaveBeenCalledWith(mockNewItem);
            expect(onCloseMock).toHaveBeenCalled();
        });
    });
});
