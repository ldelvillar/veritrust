import type { ComponentProps, ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import HistoryResultsTable from './HistoryResultsTable';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

type HistoryItem = ComponentProps<
  typeof HistoryResultsTable
>['history'][number];

function doneItem(overrides: Partial<HistoryItem>): HistoryItem {
  return {
    analysis_id: '11111111-1111-1111-1111-111111111111',
    source_type: 'text',
    origin: 'web',
    input_text: 'La vitamina C previene el resfriado',
    status: 'done',
    created_at: '2026-09-01T10:00:00Z',
    verdict: 'uncertain',
    credibility: null,
    confidence_level: null,
    ...overrides,
  };
}

function renderRow(item: HistoryItem) {
  render(
    <HistoryResultsTable
      history={[item]}
      totalCount={1}
      currentPage={1}
      pageSize={10}
      isLoading={false}
      onPageChange={() => {}}
      onDelete={() => {}}
      hasActiveFilters={false}
      onClearFilters={() => {}}
    />
  );
}

describe('HistoryResultsTable', () => {
  it.each([
    {
      verdict: 'real',
      label: 'verdadera',
      credibility: 67,
      shown: 'Verdadero',
    },
    { verdict: 'fake', label: 'falsa', credibility: 50, shown: 'Falso' },
  ] as const)(
    'badges a $verdict Verdict as $shown whatever its Credibility ($credibility)',
    ({ verdict, label, credibility, shown }) => {
      renderRow(doneItem({ verdict, label, credibility }));

      expect(screen.getByText(shown)).toBeInTheDocument();
      expect(screen.queryByText('Dudoso')).toBeNull();
      expect(
        screen.getByLabelText(`Credibilidad: ${credibility}/100`)
      ).toBeInTheDocument();
    }
  );

  it('badges an uncertain Verdict as "Dudoso" with no Credibility gauge', () => {
    renderRow(doneItem({ verdict: 'uncertain', label: 'incierta' }));

    expect(screen.getByText('Dudoso')).toBeInTheDocument();
    expect(screen.queryByLabelText(/Credibilidad:/)).toBeNull();
  });
});
