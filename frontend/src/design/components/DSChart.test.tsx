import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { DSChart } from './DSChart';

const OriginalResizeObserver = global.ResizeObserver;

beforeAll(() => {
    // jsdom reports zero dimensions by default. ChartWrapper uses a ResizeObserver
    // backed measurement, so without a non-zero bounding rect it will render the
    // placeholder instead of the chart children.
    class MockResizeObserver {
        observe = vi.fn();
        unobserve = vi.fn();
        disconnect = vi.fn();
    }
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
        width: 800,
        height: 300,
        top: 0,
        left: 0,
        bottom: 300,
        right: 800,
        x: 0,
        y: 0,
        toJSON: () => {},
    } as DOMRect);
});

afterAll(() => {
    vi.restoreAllMocks();
    global.ResizeObserver = OriginalResizeObserver;
});

// Full stub of recharts for jsdom. Recharts' ResponsiveContainer measures
// dimensions with ResizeObserver, which under jsdom always resolves to 0 — and
// several chart internals bail out silently when they detect zero dims. We
// therefore replace the whole module with deterministic, queryable stubs.
// data-* attributes let assertions verify props propagation and branch
// coverage without relying on Recharts' internal SVG structure.
vi.mock('recharts', () => ({
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="responsive-container">{children}</div>
    ),
    LineChart: ({ children, data }: any) => (
        <div data-chart="line" data-points={data?.length ?? 0}>
            {children}
        </div>
    ),
    AreaChart: ({ children, data }: any) => (
        <div data-chart="area" data-points={data?.length ?? 0}>
            {children}
        </div>
    ),
    BarChart: ({ children, data }: any) => (
        <div data-chart="bar" data-points={data?.length ?? 0}>
            {children}
        </div>
    ),
    Line: ({ stroke }: any) => (
        <span className="recharts-line" data-stroke={stroke} />
    ),
    Area: ({ stroke, fill }: any) => (
        <span className="recharts-area" data-stroke={stroke} data-fill={fill} />
    ),
    Bar: ({ fill }: any) => <span className="recharts-bar" data-fill={fill} />,
    CartesianGrid: () => <span data-testid="grid" />,
    XAxis: () => <span data-testid="xaxis" />,
    YAxis: () => <span data-testid="yaxis" />,
    Tooltip: () => null,
}));

const sampleData = [
    { label: 'Ene', value: 30 },
    { label: 'Feb', value: 55 },
    { label: 'Mar', value: 70 },
];

describe('DSChart', () => {
    describe('empty state', () => {
        it('renders a styled placeholder div when data is empty', () => {
            const { container } = render(<DSChart data={[]} height={180} />);
            expect(container.querySelector('[data-chart]')).toBeNull();
            const wrapper = container.firstChild as HTMLElement;
            expect(wrapper.tagName).toBe('DIV');
        });

        it('honors the height prop on the empty placeholder', () => {
            const { container } = render(<DSChart data={[]} height={420} />);
            const wrapper = container.firstChild as HTMLElement;
            expect(wrapper.style.height).toBe('420px');
        });
    });

    describe('chart type dispatch', () => {
        it('renders a line chart by default (type omitted → fallthrough branch)', () => {
            const { container } = render(<DSChart data={sampleData} />);
            const root = container.querySelector('[data-chart="line"]');
            expect(root).toBeInTheDocument();
            expect(root?.getAttribute('data-points')).toBe(
                String(sampleData.length)
            );
            expect(container.querySelector('[data-chart="area"]')).toBeNull();
            expect(container.querySelector('[data-chart="bar"]')).toBeNull();
        });

        it('renders an area chart with a gradient fill when type="area"', () => {
            const { container } = render(<DSChart type="area" data={sampleData} />);
            const root = container.querySelector('[data-chart="area"]');
            expect(root).toBeInTheDocument();
            const area = container.querySelector('.recharts-area');
            expect(area).toBeInTheDocument();
            // AreaChartView uses useId() to mint a unique gradient id
            expect(area?.getAttribute('data-fill')).toMatch(/^url\(#/);
            expect(container.querySelector('[data-chart="line"]')).toBeNull();
            expect(container.querySelector('[data-chart="bar"]')).toBeNull();
        });

        it('renders same-point gradient across two consecutive mounts', () => {
            const { container: a } = render(
                <DSChart type="area" data={sampleData} />
            );
            const { container: b } = render(
                <DSChart type="area" data={sampleData} />
            );
            const fillA = a.querySelector('.recharts-area')?.getAttribute('data-fill');
            const fillB = b.querySelector('.recharts-area')?.getAttribute('data-fill');
            // Each mount uses useId() — fills should be valid url(#…) ids
            expect(fillA).toMatch(/^url\(#.+?\)$/);
            expect(fillB).toMatch(/^url\(#.+?\)$/);
        });

        it('renders a bar chart when type="bar"', () => {
            const { container } = render(<DSChart type="bar" data={sampleData} />);
            const root = container.querySelector('[data-chart="bar"]');
            expect(root).toBeInTheDocument();
            expect(root?.getAttribute('data-points')).toBe(
                String(sampleData.length)
            );
            expect(container.querySelector('[data-chart="line"]')).toBeNull();
            expect(container.querySelector('[data-chart="area"]')).toBeNull();
        });
    });

    describe('propagation of color', () => {
        it('writes the custom color into the line stroke', () => {
            const { container } = render(
                <DSChart type="line" data={sampleData} color="#ff00aa" />
            );
            const line = container.querySelector('.recharts-line');
            expect(line).toBeInTheDocument();
            expect(line?.getAttribute('data-stroke')).toBe('#ff00aa');
        });

        it('writes the custom color into the area stroke', () => {
            const { container } = render(
                <DSChart type="area" data={sampleData} color="#00ffaa" />
            );
            const area = container.querySelector('.recharts-area');
            expect(area).toBeInTheDocument();
            expect(area?.getAttribute('data-stroke')).toBe('#00ffaa');
        });

        it('writes the custom color into the bar fill', () => {
            const { container } = render(
                <DSChart type="bar" data={sampleData} color="#ffaa00" />
            );
            const bar = container.querySelector('.recharts-bar');
            expect(bar).toBeInTheDocument();
            expect(bar?.getAttribute('data-fill')).toBe('#ffaa00');
        });

        it('uses the default primary color when none is provided', () => {
            const { container } = render(<DSChart type="line" data={sampleData} />);
            const line = container.querySelector('.recharts-line');
            expect(line).toBeInTheDocument();
            expect(line?.getAttribute('data-stroke')).toBe('hsl(var(--primary))');
        });
    });
});
