import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SourcesCard from './SourcesCard';

describe('SourcesCard', () => {
  it('shows the average credibility it receives instead of recomputing it', () => {
    render(
      <SourcesCard
        items={[
          { source_type: 'text', total: 1, average_credibility: 90 },
          { source_type: 'url', total: 1, average_credibility: null },
        ]}
        averageCredibility={90}
      />
    );

    expect(screen.getByText('90%')).toBeInTheDocument();
  });

  it('shows no average credibility when every analysis is uncertain', () => {
    render(
      <SourcesCard
        items={[{ source_type: 'text', total: 2, average_credibility: null }]}
        averageCredibility={null}
      />
    );

    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
