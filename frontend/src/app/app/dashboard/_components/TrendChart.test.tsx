import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrendChart from './TrendChart';

describe('TrendChart', () => {
  it('breaks the credibility line on days without credibility', () => {
    const { container } = render(
      <TrendChart
        data={[
          { date: '2026-09-01', total: 1, average_credibility: 50 },
          { date: '2026-09-02', total: 2, average_credibility: 60 },
          { date: '2026-09-03', total: 0, average_credibility: null },
          { date: '2026-09-04', total: 1, average_credibility: 70 },
        ]}
      />
    );

    const line = container.querySelector('path');
    expect(line?.getAttribute('d')?.match(/M/g)).toHaveLength(2);
    expect(container.querySelectorAll('circle')).toHaveLength(3);
  });
});
