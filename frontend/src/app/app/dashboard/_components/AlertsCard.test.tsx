import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AlertsCard from './AlertsCard';
import type { DashboardAlertItem } from './types';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

function alert(overrides: Partial<DashboardAlertItem>): DashboardAlertItem {
  return {
    id: '1',
    source_type: 'text',
    input_text: 'Beber lejía diluida elimina el virus',
    label: 'falsa',
    confidence: 0.8,
    created_at: '2026-10-01T10:00:00Z',
    verdict: 'fake',
    credibility: 20,
    ...overrides,
  };
}

describe('AlertsCard', () => {
  it('shows a false alert with its Credibility', () => {
    render(<AlertsCard items={[alert({})]} total={1} />);

    expect(screen.getByText('Falso')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('shows a partly false alert with no Credibility instead of zero', () => {
    render(
      <AlertsCard
        items={[
          alert({
            label: 'parcialmente falsa',
            verdict: 'mixed',
            credibility: null,
          }),
        ]}
        total={1}
      />
    );

    expect(screen.getByText('Parcialmente falso')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
