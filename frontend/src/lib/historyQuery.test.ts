import { describe, expect, it } from 'vitest';
import {
  DEFAULT_HISTORY_FILTERS,
  INITIAL_HISTORY_PATH,
  historyExportPath,
  historyPath,
  isExportable,
  parseHistoryFilters,
  parseHistoryPage,
  type HistoryFilters,
} from './historyQuery';

const FILTERS: HistoryFilters = {
  search: 'gripe aviar',
  sourceType: 'url',
  verdict: 'fake',
  status: 'failed',
  dateRange: '30d',
  sort: 'credibility_low',
};

describe('historyQuery', () => {
  it('precharges on the server the exact path an unfiltered client asks for', () => {
    const empty = new URLSearchParams('');

    expect(
      historyPath(parseHistoryFilters(empty), parseHistoryPage(empty))
    ).toBe(INITIAL_HISTORY_PATH);
    expect(INITIAL_HISTORY_PATH).toBe(
      '/history?page=1&page_size=10&source_type=all&verdict=all&status=all&date_range=all&sort=recent'
    );
  });

  it('reads back the filters it wrote into a path', () => {
    const query = historyPath(FILTERS, 2).split('?')[1];

    expect(parseHistoryFilters(new URLSearchParams(query))).toEqual(FILTERS);
    expect(parseHistoryPage(new URLSearchParams(query))).toBe(2);
  });

  it('falls back to the defaults for values off the contract', () => {
    const params = new URLSearchParams(
      'source_type=pdf&verdict=constructor&status=toString&date_range=1y&sort=zzz&page=-2'
    );

    expect(parseHistoryFilters(params)).toEqual(DEFAULT_HISTORY_FILTERS);
    expect(parseHistoryPage(params)).toBe(1);
  });

  it('exports with every filter, the status included, and no page', () => {
    expect(historyExportPath(FILTERS)).toBe(
      '/history/export?source_type=url&verdict=fake&status=failed&date_range=30d&sort=credibility_low&search=gripe+aviar'
    );
  });

  it.each([
    ['all', true],
    ['done', true],
    ['pending', false],
    ['failed', false],
  ] as const)('exports under status %s: %s', (status, expected) => {
    expect(isExportable(status)).toBe(expected);
  });
});
