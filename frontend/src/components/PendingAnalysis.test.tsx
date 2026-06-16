import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PendingAnalysis from './PendingAnalysis';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const minutesAgoIso = (minutes: number) =>
  new Date(Date.now() - minutes * 60_000).toISOString();

describe('PendingAnalysis', () => {
  it('shows the time estimate and no escape hatch within the expected window', () => {
    render(<PendingAnalysis createdAt={minutesAgoIso(1)} stage="extractor" />);

    expect(screen.getByText(/Tiempo estimado: 8 min/)).toBeInTheDocument();
    expect(screen.queryByText('Está tardando más de lo habitual')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Ir al historial' })).toBeNull();
  });

  it('surfaces an escape hatch once the analysis is overdue', () => {
    render(
      <PendingAnalysis createdAt={minutesAgoIso(11)} stage="investigator" />
    );

    expect(
      screen.getByText('Está tardando más de lo habitual')
    ).toBeInTheDocument();
    expect(screen.queryByText(/Tiempo estimado: 8 min/)).toBeNull();
    expect(
      screen.getByRole('link', { name: 'Ir al historial' })
    ).toHaveAttribute('href', '/app/historial');
    expect(
      screen.getByRole('link', { name: 'Analizar otro contenido' })
    ).toHaveAttribute('href', '/app/analisis');
  });
});
