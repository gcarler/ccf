import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TaskAttachmentSection from './TaskAttachmentSection';
import type { ProjectTaskRecord } from '@/types/projects';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    user: null,
    loading: false,
    isAuthenticated: true,
  }),
}));

const taskWithAttachments: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
  attachments: [
    {
      id: 'att1',
      task_id: 't1',
      filename: 'design.pdf',
      file_url: 'https://example.com/design.pdf',
      file_size: 2048,
    },
    {
      id: 'att2',
      task_id: 't1',
      filename: 'notes.txt',
      file_url: 'https://example.com/notes.txt',
      file_size: 512,
    },
  ],
};

const taskEmpty: ProjectTaskRecord = {
  id: 't2',
  project_id: 'p1',
  title: 'Empty task',
  status: 'todo',
  priority: 'medium',
  attachments: [],
};

describe('TaskAttachmentSection', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset();
  });

  it('renders attachments with filenames', () => {
    render(
      <TaskAttachmentSection
        task={taskWithAttachments}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    expect(screen.getByText('design.pdf')).toBeInTheDocument();
    expect(screen.getByText('notes.txt')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('provides a named section and unique accessible actions for every attachment', async () => {
    const onDelete = vi.fn();
    const { container } = render(
      <TaskAttachmentSection
        task={taskWithAttachments}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={onDelete}
        onUploadingChange={vi.fn()}
      />
    );

    expect(
      screen.getByRole('heading', { name: 'Archivos 2' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', {
        name: 'Abrir archivo design.pdf en una pestaña nueva',
      })
    ).toHaveAttribute('target', '_blank');
    expect(
      screen.getByRole('button', { name: 'Eliminar archivo design.pdf' })
    ).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(2);
    expect((await axe(container)).violations).toEqual([]);
  });

  it('does not render unsafe attachment URLs as clickable links', () => {
    const unsafeTask: ProjectTaskRecord = {
      ...taskWithAttachments,
      attachments: [
        {
          id: 'att-js',
          task_id: 't1',
          filename: 'ejecutable.txt',
          file_url: 'javascript:alert(1)',
        },
        {
          id: 'att-host',
          task_id: 't1',
          filename: 'externo.txt',
          file_url: '//attacker.example/file',
        },
      ],
    };

    render(
      <TaskAttachmentSection
        task={unsafeTask}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getAllByText('Enlace no disponible')).toHaveLength(2);
  });

  it('renders empty state when no attachments', () => {
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    expect(screen.getByText('Sin archivos adjuntos aun.')).toBeInTheDocument();
  });

  it('expone botón Adjuntar que abre el selector de archivos (QA-003)', () => {
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    const attachBtn = screen.getByRole('button', { name: /adjuntar/i });
    expect(attachBtn).toBeEnabled();

    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const clickSpy = vi.spyOn(input, 'click');
    fireEvent.click(attachBtn);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it('deshabilita el botón mientras uploading=true', () => {
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={true}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: /subiendo/i })).toBeDisabled();
  });

  it('sube el archivo multipart y notifica el éxito', async () => {
    const onUpload = vi.fn();
    const onUploadingChange = vi.fn();
    const updatedTask: ProjectTaskRecord = {
      ...taskEmpty,
      attachments: [
        {
          id: 'att9',
          task_id: 't2',
          filename: 'nuevo.png',
          file_url: '/uploads/nuevo.png',
          file_size: 10,
        },
      ],
    };
    vi.mocked(apiFetch).mockResolvedValueOnce(
      updatedTask as unknown as Record<string, unknown>
    );

    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={onUpload}
        onDelete={vi.fn()}
        onUploadingChange={onUploadingChange}
      />
    );
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(['contenido'], 'nuevo.png', { type: 'image/png' });

    await waitFor(() => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        '/projects/p1/tasks/t2/attachments',
        expect.objectContaining({ method: 'POST' })
      );
    });
    const [, options] = vi.mocked(apiFetch).mock.calls[0] as unknown as [
      string,
      { body: FormData },
    ];
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get('file')).toBeTruthy();

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledWith(updatedTask);
    });
    expect(onUploadingChange).toHaveBeenNthCalledWith(1, true);
    expect(onUploadingChange).toHaveBeenNthCalledWith(2, false);
    expect(toast.success).toHaveBeenCalledWith('Archivo adjuntado');
  });

  it('rechaza archivos que superan el límite de 10MB sin llamar a la API', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({});
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const big = new File([new ArrayBuffer(11 * 1024 * 1024)], 'grande.bin', {
      type: 'application/octet-stream',
    });

    await waitFor(() => {
      fireEvent.change(input, { target: { files: [big] } });
    });

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining('supera el límite')
      );
    });
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it('muestra toast de error cuando la subida falla', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('boom'));
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
      />
    );
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const file = new File(['x'], 'falla.png', { type: 'image/png' });

    await waitFor(() => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Error al subir "falla.png"');
    });
  });

  it('dispara la selección desde una ref externa compartida (clip del header)', () => {
    const externalRef = React.createRef<HTMLInputElement>();
    render(
      <TaskAttachmentSection
        task={taskEmpty}
        uploading={false}
        deletingAttachmentId={null}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onUploadingChange={vi.fn()}
        externalInputRef={externalRef}
      />
    );
    const input = document.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    expect(externalRef.current).toBe(input);
    const clickSpy = vi.spyOn(input, 'click');
    externalRef.current?.click();
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });
});
