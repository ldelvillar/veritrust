import type { ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Pricing from './Pricing';

let isSignedIn = false;

vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ isSignedIn }),
}));

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('Pricing', () => {
  afterEach(() => {
    isSignedIn = false;
  });

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

  it('sends a signed-out visitor to sign up and back to the plan card', () => {
    render(<Pricing />);

    expect(screen.getByRole('link', { name: 'Hazte Pro' })).toHaveAttribute(
      'href',
      '/registro?redirect_url=%2Fapp%2Fcuenta%23plan'
    );
  });

  it('sends a signed-in user straight to the plan card', () => {
    isSignedIn = true;
    render(<Pricing />);

    expect(screen.getByRole('link', { name: 'Hazte Pro' })).toHaveAttribute(
      'href',
      '/app/cuenta#plan'
    );
  });
});
