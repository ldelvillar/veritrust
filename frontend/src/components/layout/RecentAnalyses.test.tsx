import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { HistoryItem } from '@/lib/historyQuery';
import RecentAnalyses from './RecentAnalyses';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const item = (overrides: Partial<HistoryItem>): HistoryItem => ({
  analysis_id: 'id',
  source_type: 'text',
  origin: 'web',
  input_text: 'Texto analizado',
  status: 'done',
  created_at: '2026-10-21T10:00:00Z',
  verdict: 'fake',
  credibility: 12,
  confidence_level: null,
  ...overrides,
});

describe('RecentAnalyses', () => {
  it('renders nothing without analyses', () => {
    const { container } = render(<RecentAnalyses items={[]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('links each analysis to its report and names its status', () => {
    render(
      <RecentAnalyses
        items={[
          item({ analysis_id: 'a', input_text: 'El 5G debilita' }),
          item({ analysis_id: 'b', status: 'pending', input_text: 'Ayuno' }),
          item({
            analysis_id: 'c',
            status: 'failed',
            error_code: 'NO_MEDICAL_CLAIMS',
            input_text: 'Receta de tarta',
          }),
        ]}
      />
    );

    expect(screen.getByRole('link', { name: 'Ver todo' })).toHaveAttribute(
      'href',
      '/app/historial'
    );
    expect(
      screen.getByRole('link', { name: 'Falso: El 5G debilita' })
    ).toHaveAttribute('href', '/app/analisis/a');
    expect(
      screen.getByRole('link', { name: 'En curso: Ayuno' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Sin afirmaciones: Receta de tarta' })
    ).toBeInTheDocument();
  });
});
