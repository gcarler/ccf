import { useRef } from 'react';
import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { useResizablePanel } from '@/hooks/useResizablePanel';
import { PanelResizeHandle } from './PanelResizeHandle';

function Example() {
  const panelRef = useRef<HTMLDivElement>(null);
  const resize = useResizablePanel({
    storageKey: 'storybook:panel-width',
    defaultWidth: 480,
    panelRef,
  });
  return (
    <div
      ref={panelRef}
      style={resize.style}
      className="relative ml-auto h-80 bg-[hsl(var(--surface-1))] p-6 text-[hsl(var(--foreground))]"
    >
      <PanelResizeHandle resize={resize} />
      <p>
        Arrastra el borde izquierdo o usa las flechas para ajustar el ancho.
      </p>
    </div>
  );
}
const meta = {
  title: 'UI/PanelResizeHandle',
  component: Example,
} satisfies Meta<typeof Example>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
