'use client';

import type { MinistryEvent } from '@/app/plataforma/evangelism/types';
import ErrorBoundary from '@/components/ErrorBoundary';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { Download } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useEffect, useRef, useState } from 'react';

interface EventQrDrawerProps {
  isOpen: boolean;
  selectedEvent: MinistryEvent | null;
  onClose: () => void;
}

export default function EventQrDrawer({ isOpen, selectedEvent, onClose }: EventQrDrawerProps) {
  const qrContainerRef = useRef<HTMLDivElement>(null);
  const [origin, setOrigin] = useState('');

  useEffect(() => {
    setOrigin(window.location.origin);
  }, []);

  const registrationUrl = origin && selectedEvent
    ? `${origin}/public/register?event_id=${selectedEvent.id}`
    : '';

  const downloadQr = () => {
    const svg = qrContainerRef.current?.querySelector('svg');
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      if (ctx) {
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0);
      }
      const pngFile = canvas.toDataURL('image/png');
      const downloadLink = document.createElement('a');
      downloadLink.download = `QR_${selectedEvent?.name}.png`;
      downloadLink.href = pngFile;
      downloadLink.click();
    };
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
  };

  return (
    <ErrorBoundary moduleName="Eventos - QR" compact>
      <WorkspaceDrawer
        isOpen={isOpen}
        onClose={onClose}
        title="Código QR de registro"
        subtitle={selectedEvent?.name ?? 'Evento'}
        actions={
          <button
            onClick={downloadQr}
            className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2"
          >
            <Download size={14} /> Descargar
          </button>
        }
      >
        <div className="flex flex-col items-center justify-center space-y-3 py-1.5">
          <div
            ref={qrContainerRef}
            className="p-4 bg-[hsl(var(--bg-primary))] rounded-md shadow-xl border border-[hsl(var(--border-primary))] flex items-center justify-center"
          >
            <QRCodeSVG
              value={registrationUrl}
              size={256}
              level="H"
              includeMargin={true}
            />
          </div>
          <div className="text-center space-y-2">
            <p className="text-sm font-bold text-[hsl(var(--text-primary))]">Escanea para registrarte</p>
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Enlace de Registro</p>
            <a
              href={registrationUrl || '#'}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors break-all bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.1)] px-4 py-2 rounded-md inline-block mt-2"
            >
              {registrationUrl}
            </a>
          </div>
        </div>
      </WorkspaceDrawer>
    </ErrorBoundary>
  );
}
