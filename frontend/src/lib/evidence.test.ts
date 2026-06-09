import { describe, expect, it } from 'vitest';
import { countBackedClaims, groupSourcesByClaim } from './evidence';

const claim = (text: string) => ({ text, label: 'verdadera', confidence: 0.9 });
const source = (url: string, statements: string[] | null) => ({
  title: `Paper ${url}`,
  url,
  statements,
});

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

describe('countBackedClaims', () => {
  it('counts only claims with at least one matching source', () => {
    expect(
      countBackedClaims(
        [claim('a'), claim('b'), claim('c')],
        [source('u1', ['a']), source('u2', ['a']), source('u3', ['c'])]
      )
    ).toEqual({ backed: 2, total: 3 });
  });

  it('reports zero backed when sources match no claim', () => {
    expect(
      countBackedClaims([claim('a'), claim('b')], [source('u1', ['z'])])
    ).toEqual({ backed: 0, total: 2 });
  });

  it('reports zero backed when there are no sources', () => {
    expect(countBackedClaims([claim('a')], [])).toEqual({
      backed: 0,
      total: 1,
    });
  });
});
