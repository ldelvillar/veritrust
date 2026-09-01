import { describe, expect, it } from 'vitest';
import { groupSourcesByClaim, summarizeStances } from './evidence';

const claim = (text: string) => ({ text, label: 'verdadera', confidence: 0.9 });
const source = (url: string, claimIndices: number[] | null) => ({
  title: `Paper ${url}`,
  url,
  statements:
    claimIndices?.map(claim_index => ({
      claim_index,
      text: `claim ${claim_index}`,
      stance: null,
    })) ?? null,
});
const stanced = (
  url: string,
  statements: { claim_index: number; stance: string | null }[]
) => ({
  title: `Paper ${url}`,
  url,
  statements: statements.map(s => ({ ...s, text: `claim ${s.claim_index}` })),
});

describe('groupSourcesByClaim', () => {
  it('nests a source under the claim it supports', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a'), claim('b')],
      [source('u1', [0])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
    expect(groups[1].sources).toEqual([]);
    expect(unmatched).toEqual([]);
  });

  it('links a shared source to every claim it supports', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a'), claim('b')],
      [source('u1', [0, 1])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
    expect(groups[1].sources.map(s => s.url)).toEqual(['u1']);
    expect(unmatched).toEqual([]);
  });

  it('sends sources whose claim index is out of range to unmatched', () => {
    const { groups, unmatched } = groupSourcesByClaim(
      [claim('a')],
      [source('u1', [4])]
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

  it('keeps two claims with identical text on their own evidence', () => {
    const { groups } = groupSourcesByClaim(
      [claim('misma frase'), claim('misma frase')],
      [source('u1', [0]), source('u2', [1])]
    );

    expect(groups[0].sources.map(s => s.url)).toEqual(['u1']);
    expect(groups[1].sources.map(s => s.url)).toEqual(['u2']);
  });

  it('keeps a claim with no evidence as an empty group', () => {
    const { groups } = groupSourcesByClaim([claim('a')], []);

    expect(groups).toHaveLength(1);
    expect(groups[0].sources).toEqual([]);
  });
});

describe('summarizeStances', () => {
  it('tallies supports, contradicts and inconclusive for the claim', () => {
    const summary = summarizeStances(0, [
      stanced('u1', [{ claim_index: 0, stance: 'supports' }]),
      stanced('u2', [{ claim_index: 0, stance: 'supports' }]),
      stanced('u3', [{ claim_index: 0, stance: 'contradicts' }]),
      stanced('u4', [{ claim_index: 0, stance: 'inconclusive' }]),
    ]);

    expect(summary).toEqual({ supports: 2, contradicts: 1, inconclusive: 1 });
  });

  it('only counts the stance on the given claim, not on other claims', () => {
    const summary = summarizeStances(0, [
      stanced('u1', [
        { claim_index: 1, stance: 'supports' },
        { claim_index: 0, stance: 'contradicts' },
      ]),
    ]);

    expect(summary).toEqual({ supports: 0, contradicts: 1, inconclusive: 0 });
  });

  it('ignores sources without a resolved stance', () => {
    const summary = summarizeStances(0, [
      stanced('u1', [{ claim_index: 0, stance: null }]),
      { title: 'u2', url: 'u2', statements: null },
    ]);

    expect(summary).toEqual({ supports: 0, contradicts: 0, inconclusive: 0 });
  });

  it('does not attribute a stance to a claim that only shares its text', () => {
    const summary = summarizeStances(1, [
      stanced('u1', [{ claim_index: 0, stance: 'supports' }]),
    ]);

    expect(summary).toEqual({ supports: 0, contradicts: 0, inconclusive: 0 });
  });
});
