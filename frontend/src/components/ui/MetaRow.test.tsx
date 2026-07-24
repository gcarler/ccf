import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MetaRow from './MetaRow';

describe('MetaRow', () => {
    it('renders the label', () => {
        render(
            <MetaRow icon={<span data-testid="icon">★</span>} label="Nombre">
                <span>Valor</span>
            </MetaRow>
        );
        expect(screen.getByText('Nombre')).toBeInTheDocument();
    });

    it('renders children content', () => {
        render(
            <MetaRow icon={<span data-testid="icon">★</span>} label="Etiqueta">
                <span data-testid="child">Contenido hijo</span>
            </MetaRow>
        );
        expect(screen.getByTestId('child')).toHaveTextContent('Contenido hijo');
    });

    it('renders the icon element', () => {
        render(
            <MetaRow icon={<span data-testid="icon">★</span>} label="Etiqueta">
                <span>Valor</span>
            </MetaRow>
        );
        expect(screen.getByTestId('icon')).toBeInTheDocument();
    });
});
