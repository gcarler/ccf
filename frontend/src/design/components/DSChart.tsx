"use client";

import React, { useId } from 'react';
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { colors } from '../tokens';

interface ChartDataPoint {
    label: string;
    value: number;
}

type ChartType = 'line' | 'area' | 'bar';

interface DSChartProps {
    type?: ChartType;
    data?: ChartDataPoint[];
    height?: number;
    color?: string;
}

const CHART_COLORS = {
    grid: 'rgba(255,255,255,0.05)',
    tick: colors.slate[500],
    tooltipBg: colors.slate[900],
    tooltipText: '#fff',
};

function ChartWrapper({ children, height }: { children: React.ReactNode; height: number }) {
    return (
        <div style={{ width: '100%', height, minWidth: 0, minHeight: 0 }}>
            <ResponsiveContainer>
                {children}
            </ResponsiveContainer>
        </div>
    );
}

function ChartTooltip() {
    return (
        <Tooltip
            contentStyle={{
                backgroundColor: CHART_COLORS.tooltipBg,
                border: 'none',
                borderRadius: '8px',
                fontSize: '10px',
            }}
            itemStyle={{ color: CHART_COLORS.tooltipText }}
        />
    );
}

function ChartGrid() {
    return (
        <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke={CHART_COLORS.grid}
        />
    );
}

function ChartXAxis() {
    return (
        <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: CHART_COLORS.tick }}
        />
    );
}

function ChartYAxis() {
    return <YAxis hide />;
}

function LineChartView({ data, color }: { data: ChartDataPoint[]; color: string }) {
    return (
        <ChartWrapper height={300}>
            <LineChart data={data}>
                <ChartGrid />
                <ChartXAxis />
                <ChartYAxis />
                <ChartTooltip />
                <Line
                    type="monotone"
                    dataKey="value"
                    stroke={color}
                    strokeWidth={3}
                    dot={{ r: 4, fill: color }}
                    activeDot={{ r: 6 }}
                />
            </LineChart>
        </ChartWrapper>
    );
}

function AreaChartView({ data, color, gradientId }: { data: ChartDataPoint[]; color: string; gradientId: string }) {
    return (
        <ChartWrapper height={300}>
            <AreaChart data={data}>
                <defs>
                    <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                </defs>
                <ChartGrid />
                <ChartXAxis />
                <ChartYAxis />
                <ChartTooltip />
                <Area
                    type="monotone"
                    dataKey="value"
                    stroke={color}
                    fillOpacity={1}
                    fill={`url(#${gradientId})`}
                    strokeWidth={2}
                />
            </AreaChart>
        </ChartWrapper>
    );
}

function BarChartView({ data, color }: { data: ChartDataPoint[]; color: string }) {
    return (
        <ChartWrapper height={300}>
            <BarChart data={data}>
                <ChartGrid />
                <ChartXAxis />
                <ChartYAxis />
                <ChartTooltip />
                <Bar
                    dataKey="value"
                    fill={color}
                    radius={[4, 4, 0, 0]}
                />
            </BarChart>
        </ChartWrapper>
    );
}

export function DSChart({
    type = 'line',
    data = [],
    height = 300,
    color = colors.primary[500],
}: DSChartProps) {
    const gradientId = useId();

    if (data.length === 0) {
        return <div style={{ width: '100%', height, minWidth: 0, minHeight: 0 }} />;
    }

    switch (type) {
        case 'area':
            return <AreaChartView data={data} color={color} gradientId={gradientId} />;
        case 'bar':
            return <BarChartView data={data} color={color} />;
        case 'line':
        default:
            return <LineChartView data={data} color={color} />;
    }
}
