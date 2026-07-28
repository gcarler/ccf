import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import Navbar from './Navbar';

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    logout: vi.fn(),
  }),
}));

vi.mock('@/lib/site-branding', () => ({
  useSiteBranding: () => ({
    logoUrl: null,
    logoName: 'CCF Plataforma',
  }),
}));

describe('Navbar component', () => {
  it('renders brand title and main navigation links', () => {
    render(<Navbar />);

    expect(screen.getByText('CCF Plataforma')).toBeInTheDocument();
    expect(screen.getByText('Inicio')).toBeInTheDocument();
    expect(screen.getByText('Academia')).toBeInTheDocument();
    expect(screen.getByText('Proyectos')).toBeInTheDocument();
    expect(screen.getByText('Donaciones')).toBeInTheDocument();
  });

  it('renders login and register buttons when user is not authenticated', () => {
    render(<Navbar />);

    expect(screen.getByText('Login')).toBeInTheDocument();
    expect(screen.getByText('Empezar')).toBeInTheDocument();
  });
});
