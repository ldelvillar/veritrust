import type { ReactNode } from 'react';
import { render, screen, within } from '@testing-library/react';
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
  it('shows the elapsed time and no escape hatch before the analysis is overdue', () => {
    render(<PendingAnalysis createdAt={minutesAgoIso(1)} stage="extractor" />);

    expect(screen.getByText('1:00')).toBeInTheDocument();
    expect(screen.queryByText('Está tardando más de lo habitual')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Ir al historial' })).toBeNull();
  });

  it('lists only the steps reached so far and counts the rest', () => {
    render(<PendingAnalysis createdAt={minutesAgoIso(1)} stage="translator" />);

    expect(screen.getByText('Agente Traductor')).toBeInTheDocument();
    expect(screen.queryByText('Agente Investigador')).toBeNull();
    expect(
      screen.getByText('2 pasos más antes del informe')
    ).toBeInTheDocument();
  });

  it('renders the page actions in the bottom bar', () => {
    render(
      <PendingAnalysis
        createdAt={minutesAgoIso(1)}
        stage="extractor"
        actions={<button type="button">Eliminar</button>}
      />
    );

    const bar = screen.getByText(
      'El informe aparecerá aquí en cuanto termine el análisis'
    ).parentElement?.parentElement;
    expect(bar).toBeDefined();
    expect(
      within(bar as HTMLElement).getByRole('button', { name: 'Eliminar' })
    ).toBeInTheDocument();
  });

  it('surfaces an escape hatch once the analysis is overdue', () => {
    render(
      <PendingAnalysis createdAt={minutesAgoIso(5)} stage="investigator" />
    );

    expect(
      screen.getByText('Está tardando más de lo habitual')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Ir al historial' })
    ).toHaveAttribute('href', '/app/historial');
    expect(
      screen.getByRole('link', { name: 'Analizar otro contenido' })
    ).toHaveAttribute('href', '/app/analisis');
  });
});
