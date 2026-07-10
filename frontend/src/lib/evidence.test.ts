import { describe, expect, it } from 'vitest';
import { groupSourcesByClaim, summarizeStances } from './evidence';

const claim = (text: string) => ({ text, label: 'verdadera', confidence: 0.9 });
const source = (url: string, statements: string[] | null) => ({
  title: `Paper ${url}`,
  url,
  statements: statements?.map(text => ({ text, stance: null })) ?? null,
});
const stanced = (
  url: string,
  statements: { text: string; stance: string | null }[]
) => ({ title: `Paper ${url}`, url, statements });

describe('groupSourcesByClaim', () => {
  it('nests a source under the claim it supports', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a'), claim('b')],
      [source('u1', ['a'])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
    expect(groups[1].sources).toEqual([]);
    expect(unmatched).toEqual([]);
  });

  it('links a shared source to every claim it supports', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a'), claim('b')],
      [source('u1', ['a', 'b'])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
    expect(groups[1].sources.map(s => s.url)).toEqual(['u1']);
    expect(unmatched).toEqual([]);
  });

  it('sends sources with no matching statement to unmatched', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a')],
      [source('u1', ['c'])]
    );

    expect(groups[0].sources).toEqual([]);
    expect(unmatched.map(s => s.url)).toEqual(['u1']);
  });

  it('treats empty or null statements as unmatched', () => {
    const { unmatched } = groupSourcesByClaim(
      [claim('a')],
      [source('u1', []), source('u2', null)]
    );

    expect(unmatched.map(s => s.url)).toEqual(['u1', 'u2']);
  });

  it('matches ignoring surrounding whitespace', () => {
    const { groups } = groupSourcesByClaim(
      [claim('a')],
      [source('u1', ['  a  '])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
  });

  it('keeps a claim with no evidence as an empty group', () => {
    const { groups } = groupSourcesByClaim([claim('a')], []);

    expect(groups).toHaveLength(1);
    expect(groups[0].sources).toEqual([]);
  });
});

describe('summarizeStances', () => {
  it('tallies supports, contradicts and inconclusive for the claim', () => {
    const summary = summarizeStances(claim('a'), [
      stanced('u1', [{ text: 'a', stance: 'supports' }]),
      stanced('u2', [{ text: 'a', stance: 'supports' }]),
      stanced('u3', [{ text: 'a', stance: 'contradicts' }]),
      stanced('u4', [{ text: 'a', stance: 'inconclusive' }]),
    ]);

    expect(summary).toEqual({ supports: 2, contradicts: 1, inconclusive: 1 });
  });

  it('only counts the stance on the given claim, not on other claims', () => {
    const summary = summarizeStances(claim('a'), [
      stanced('u1', [
        { text: 'b', stance: 'supports' },
        { text: 'a', stance: 'contradicts' },
      ]),
    ]);

    expect(summary).toEqual({ supports: 0, contradicts: 1, inconclusive: 0 });
  });

  it('ignores sources without a resolved stance', () => {
    const summary = summarizeStances(claim('a'), [
      stanced('u1', [{ text: 'a', stance: null }]),
      { title: 'u2', url: 'u2', statements: null },
    ]);

    expect(summary).toEqual({ supports: 0, contradicts: 0, inconclusive: 0 });
  });

  it('matches ignoring surrounding whitespace', () => {
    const summary = summarizeStances(claim('a'), [
      stanced('u1', [{ text: '  a  ', stance: 'supports' }]),
    ]);

    expect(summary.supports).toBe(1);
  });
});
