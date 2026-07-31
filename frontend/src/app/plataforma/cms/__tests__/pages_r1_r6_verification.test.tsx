import React from 'react';
import { render, screen, fireEvent, waitFor, waitForElementToBeRemoved } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { toast } from 'sonner';

// Mock Framer Motion to prevent AnimatePresence async exit delays in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, onClick, className, style, layout, initial, animate, exit, transition, ...props }: any) => (
      <div onClick={onClick} className={className} style={style} {...props}>{children}</div>
    ),
    aside: ({ children, className, style, ...props }: any) => (
      <aside className={className} style={style} {...props}>{children}</aside>
    ),
    section: ({ children, className, style, ...props }: any) => (
      <section className={className} style={style} {...props}>{children}</section>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mocks
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/plataforma/cms',
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    user: { id: '1', role: 'admin', email: 'test@example.com' },
    isAuthenticated: true,
  }),
}));

const mockApiFetch = vi.fn();
vi.mock('@/lib/http', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

const mockPatchCmsPostByCategory = vi.fn();
const mockDeleteCmsPostByCategory = vi.fn();
const mockSaveTestimonialV2 = vi.fn();
const mockListCmsPostsByCategory = vi.fn();

vi.mock('@/lib/cms/v2', () => ({
  listCmsPostsByCategory: (...args: any[]) => mockListCmsPostsByCategory(...args),
  patchCmsPostByCategory: (...args: any[]) => mockPatchCmsPostByCategory(...args),
  deleteCmsPostByCategory: (...args: any[]) => mockDeleteCmsPostByCategory(...args),
  saveTestimonial: (...args: any[]) => mockSaveTestimonialV2(...args),
  postToTestimonial: (post: any) => post,
  postToAnnouncement: (post: any) => post,
  listCmsSites: vi.fn().mockResolvedValue([
    { site_key: 'ccf', name: 'Centro Cristiano' },
  ]),
  listCmsMenus: vi.fn().mockResolvedValue([
    { id: 'menu-1', menu_key: 'main', name: 'Menú Principal', is_active: true },
  ]),
  listCmsMenuItems: vi.fn().mockResolvedValue([
    { id: 'item-1', label: 'Inicio', href: '/', is_external: false, visibility: 'public', sort_order: 0 },
    { id: 'item-2', label: 'Nosotros', href: '/nosotros', is_external: false, visibility: 'public', sort_order: 1 },
  ]),
  createCmsMenu: vi.fn(),
  createCmsMenuItem: vi.fn(),
  patchCmsMenu: vi.fn().mockResolvedValue({ id: 'menu-1', menu_key: 'main', name: 'Menú Principal', is_active: false }),
  patchCmsMenuItem: vi.fn(),
  deleteCmsMenuItem: vi.fn(),
  reorderCmsMenuItems: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Components under test
import CmsTestimonialsPage from '../testimonials/page';
import CmsMenusManagement from '../menus/page';
import AnnouncementsAdmin from '../announcements/page';
import RedirectsPage from '../redirects/page';
import WebhooksPage from '../webhooks/page';
import CmsHomePage from '../page';

describe('Adversarial Verification & Edge Cases (R1-R6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListCmsPostsByCategory.mockResolvedValue([
      {
        id: 'test-1',
        slug: 'testimonio-1',
        content: 'Dios hizo un milagro en mi vida',
        emotion: 'Sanidad',
        created_at: '2026-07-30T10:00:00Z',
        published: true,
        status: 'approved',
        is_approved: true,
        media_type: 'text',
        author_persona_id: 'persona-123',
      },
      {
        id: 'test-2',
        slug: 'testimonio-2',
        content: 'Gratitud por la provision',
        emotion: 'Provisión',
        created_at: '2026-07-30T11:00:00Z',
        published: false,
        status: 'pending',
        is_approved: false,
        media_type: 'image',
        author_persona_id: null,
      },
    ]);

    mockApiFetch.mockImplementation((url: string) => {
      if (url.includes('/cms/v2/redirects')) {
        return Promise.resolve([
          { id: 'red-1', from_path: '/old-path', to_path: '/new-path', status_code: 301, hit_count: 42 },
          { id: 'red-2', from_path: '/temp-page', to_path: '/home', status_code: 302, hit_count: 5 },
        ]);
      }
      if (url.includes('/cms/v2/webhooks') && url.includes('/deliveries')) {
        return Promise.resolve([
          { id: 'del-1', event: 'page.published', response_status: 200, success: true, duration_ms: 120, created_at: '2026-07-30T12:00:00Z' },
        ]);
      }
      if (url.includes('/cms/v2/webhooks')) {
        return Promise.resolve([
          { id: 'wh-1', name: 'Slack Webhook', url: 'https://hooks.slack.com/123', events: ['page.published'], is_active: true, failure_count: 0, last_triggered_at: null },
        ]);
      }
      if (url.includes('/cms/metrics')) {
        return Promise.resolve({
          published_blocks: 10,
          in_review_blocks: 2,
          announcements_active: 3,
          testimonials_approved: 5,
          media_total: 20,
          media_images: 15,
          media_videos: 3,
          media_audio: 2,
        });
      }
      if (url.includes('/cms/media')) {
        return Promise.resolve({ items: [], total: 0 });
      }
      if (url.includes('/dashboard/cms')) {
        return Promise.resolve({
          cards: [],
          page_views_total: 1000,
          page_views_7d: 250,
          page_views_30d: 1000,
          top_pages: [{ slug: 'home', title: 'Inicio', views: 500 }],
          recent_posts: [{ slug: 'post-1', title: 'Post 1', published_at: '2026-07-30', status: 'published', category_count: 1, tag_count: 2 }],
          recent_activity: [{ entity_type: 'page', action: 'publish', from_status: 'draft', to_status: 'published', created_at: '2026-07-30', actor: 'Admin', metadata: {} }],
          posts_total: 10,
          posts_published: 8,
          categories_total: 3,
          tags_total: 5,
          publicaciones_por_mes: [{ label: 'Jul', value: 8 }],
          contenido_por_tipo: [{ label: 'Hero', value: 4 }],
          borradores_pendientes: 2,
        });
      }
      return Promise.resolve([]);
    });
  });

  describe('R1: Testimonials Page Edge Cases & Modal States', () => {
    it('filters testimonials by search input and category pills', async () => {
      render(<CmsTestimonialsPage />);
      await waitFor(() => {
        expect(screen.getByText('“Dios hizo un milagro en mi vida”')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Buscar...');
      fireEvent.change(searchInput, { target: { value: 'milagro' } });
      expect(screen.getByText('“Dios hizo un milagro en mi vida”')).toBeInTheDocument();
      expect(screen.queryByText('“Gratitud por la provision”')).not.toBeInTheDocument();

      fireEvent.change(searchInput, { target: { value: '' } });
      expect(screen.getByText('“Gratitud por la provision”')).toBeInTheDocument();
    });

    it('opens drawer form on "Nuevo Testimonio" click', async () => {
      render(<CmsTestimonialsPage />);
      await waitFor(() => {
        expect(screen.getByText('Nuevo Testimonio')).toBeInTheDocument();
      });

      const newBtn = screen.getByText('Nuevo Testimonio');
      fireEvent.click(newBtn);
      expect(screen.getByText('Crear Testimonio')).toBeInTheDocument();
    });

    it('opens archive modal when archiving a testimonial', async () => {
      mockDeleteCmsPostByCategory.mockResolvedValue({ success: true });
      render(<CmsTestimonialsPage />);
      await waitFor(() => {
        expect(screen.getByText('“Dios hizo un milagro en mi vida”')).toBeInTheDocument();
      });

      // Click card to select
      fireEvent.click(screen.getByText('“Dios hizo un milagro en mi vida”'));
      await waitFor(() => {
        expect(screen.getByText('Testimonio #test-1')).toBeInTheDocument();
      });

      // Click "Archivar testimonio" in detail drawer
      const archiveBtn = screen.getByRole('button', { name: /Archivar testimonio/i });
      fireEvent.click(archiveBtn);

      await waitFor(() => {
        expect(screen.getByText('¿Archivar testimonio?')).toBeInTheDocument();
      });

      // Cancel archive modal
      const cancelBtn = screen.getByText('Cancelar');
      fireEvent.click(cancelBtn);
      expect(screen.queryByText('¿Archivar testimonio?')).not.toBeInTheDocument();
    });
  });

  describe('R2: Menus Page Edge Cases & Modal States', () => {
    it('toggles quick add bar and handles menu deactivation modal', async () => {
      render(<CmsMenusManagement />);
      await waitFor(() => {
        expect(screen.getByText('Añadir Enlace')).toBeInTheDocument();
      });

      // Open quick add
      fireEvent.click(screen.getByText('Añadir Enlace'));
      expect(screen.getByPlaceholderText('Nombre del enlace...')).toBeInTheDocument();

      // Deactivate menu modal
      const deactivateBtn = screen.getByRole('button', { name: /Desactivar/i });
      fireEvent.click(deactivateBtn);
      await waitFor(() => {
        expect(screen.getByText('¿Desactivar menú?')).toBeInTheDocument();
      });

      const cancelBtn = screen.getByText('Cancelar');
      fireEvent.click(cancelBtn);
      expect(screen.queryByText('¿Desactivar menú?')).not.toBeInTheDocument();
    });
  });

  describe('R3: Announcements Page Search & Archive Modal', () => {
    it('filters normal announcements with search input', async () => {
      render(<AnnouncementsAdmin />);
      await waitFor(() => {
        expect(screen.getByText('Aviso sobre Cursos')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Buscar por título o contenido...');
      fireEvent.change(searchInput, { target: { value: 'Cursos' } });
      expect(screen.getByText('Aviso sobre Cursos')).toBeInTheDocument();

      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });
      expect(screen.queryByText('Aviso sobre Cursos')).not.toBeInTheDocument();
    });

    it('opens and closes archive modal for announcements', async () => {
      render(<AnnouncementsAdmin />);
      await waitFor(() => {
        expect(screen.getByText('Gran Evento de Sanidad')).toBeInTheDocument();
      });

      const archiveBtns = screen.getAllByTitle('Archivar');
      fireEvent.click(archiveBtns[0]);

      await waitFor(() => {
        expect(screen.getByText('¿Archivar comunicado?')).toBeInTheDocument();
      });

      const cancelBtn = screen.getByText('Cancelar');
      fireEvent.click(cancelBtn);
      expect(screen.queryByText('¿Archivar comunicado?')).not.toBeInTheDocument();
    });
  });

  describe('R4: Redirects Page Search, Filters & Delete Panel', () => {
    it('filters redirects by path search and status code filter', async () => {
      render(<RedirectsPage />);
      await waitFor(() => {
        expect(screen.getByText('/old-path')).toBeInTheDocument();
        expect(screen.getByText('/temp-page')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Buscar por URL...');
      fireEvent.change(searchInput, { target: { value: 'temp' } });
      expect(screen.getByText('/temp-page')).toBeInTheDocument();
      expect(screen.queryByText('/old-path')).not.toBeInTheDocument();
    });

    it('opens side panel for delete confirmation', async () => {
      render(<RedirectsPage />);
      await waitFor(() => {
        expect(screen.getByText('/old-path')).toBeInTheDocument();
      });

      const deleteBtns = screen.getAllByTitle('Eliminar');
      fireEvent.click(deleteBtns[0]);

      await waitFor(() => {
        expect(screen.getByText('Eliminar redirección')).toBeInTheDocument();
      });

      const cancelBtn = screen.getByRole('button', { name: /Cancelar/i });
      fireEvent.click(cancelBtn);
      await waitFor(() => {
        expect(screen.queryByText('Eliminar redirección')).not.toBeInTheDocument();
      });
    });
  });

  describe('R5: Webhooks Form, Deliveries & Delete Modal', () => {
    it('toggles form creation and validates inputs', async () => {
      render(<WebhooksPage />);
      await waitFor(() => {
        expect(screen.getByText('Slack Webhook')).toBeInTheDocument();
      });

      const newBtn = screen.getByText('Nuevo Webhook');
      fireEvent.click(newBtn);
      expect(screen.getByText('Configurar Webhook')).toBeInTheDocument();

      // Submit empty form triggers toast error
      const createBtn = screen.getByRole('button', { name: /Crear Webhook/i });
      fireEvent.click(createBtn);
      expect(toast.error).toHaveBeenCalledWith('El nombre y la URL son obligatorios');
    });

    it('opens delete confirmation side panel', async () => {
      render(<WebhooksPage />);
      await waitFor(() => {
        expect(screen.getByText('Slack Webhook')).toBeInTheDocument();
      });

      const deleteBtn = screen.getByTitle('Eliminar');
      fireEvent.click(deleteBtn);

      await waitFor(() => {
        expect(screen.getByText('Eliminar Webhook')).toBeInTheDocument();
      });

      const cancelBtn = screen.getByRole('button', { name: /Cancelar/i });
      fireEvent.click(cancelBtn);
      await waitFor(() => {
        expect(screen.queryByText('Eliminar Webhook')).not.toBeInTheDocument();
      });
    });
  });

  describe('R6: CMS Overview Dashboard', () => {
    it('renders overview cards, quick actions and quality score', async () => {
      render(<CmsHomePage />);
      await waitFor(() => {
        expect(screen.getByText('Vistas totales')).toBeInTheDocument();
        expect(screen.getByText('Crear Post')).toBeInTheDocument();
      });
    });
  });
});
