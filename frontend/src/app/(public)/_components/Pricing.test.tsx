import type { ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Pricing from './Pricing';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('Pricing', () => {
  it('shows the individual plans with the yearly price in the Pro card', () => {
    render(<Pricing />);

    expect(screen.getByRole('button', { name: 'Individual' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(
      screen.getByText('o 290€ al año (2 meses gratis)')
    ).toBeInTheDocument();
    expect(screen.queryByText('Equipo')).toBeNull();
  });

  it('switches to the team and enterprise plans', () => {
    render(<Pricing />);

    fireEvent.click(screen.getByRole('button', { name: 'Equipos y empresas' }));

    expect(screen.getByText('Equipo')).toBeInTheDocument();
    expect(screen.getByText('Institución')).toBeInTheDocument();
    expect(screen.queryByText('Pro')).toBeNull();
    expect(
      screen.getByRole('link', { name: 'Acceso anticipado' })
    ).toHaveAttribute('href', '/demo?plan=equipo');
  });
});
