import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DomainsCard from './DomainsCard';

describe('DomainsCard', () => {
  it('shows a domain’s average credibility as a number', () => {
    render(
      <DomainsCard
        items={[{ domain: 'a.com', total: 2, average_credibility: 82.4 }]}
      />
    );

    expect(screen.getByText('82%')).toBeInTheDocument();
  });

  it('shows no credibility for a domain whose analyses are all uncertain', () => {
    render(
      <DomainsCard
        items={[{ domain: 'a.com', total: 2, average_credibility: null }]}
      />
    );

    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('Baja')).not.toBeInTheDocument();
  });
});
