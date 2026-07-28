import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCard } from './StatCard';
import { Users } from 'lucide-react';

describe('StatCard component', () => {
  it('renders label and value correctly', () => {
    render(
      <StatCard
        label="Total Personas"
        value={1250}
        icon={Users}
        color="text-blue-500"
        bg="bg-blue-500/10"
      />
    );

    expect(screen.getByText('Total Personas')).toBeInTheDocument();
    expect(screen.getByText('1250')).toBeInTheDocument();
  });

  it('renders description and trend when provided', () => {
    render(
      <StatCard
        label="Nuevos Miembros"
        value="45"
        icon={Users}
        color="text-emerald-500"
        bg="bg-emerald-500/10"
        desc="+12% respecto al mes anterior"
        trend="+12%"
      />
    );

    expect(screen.getByText('+12% respecto al mes anterior')).toBeInTheDocument();
    expect(screen.getByText('+12%')).toBeInTheDocument();
  });
});
