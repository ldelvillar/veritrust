import type { paths } from '@/types/api';

type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
type ClaimType = NonNullable<ResultType['claims']>[number];
type SourceType = NonNullable<ResultType['sources']>[number];

export interface ClaimEvidence {
  claim: ClaimType;
  sources: SourceType[];
}

export interface GroupedEvidence {
  groups: ClaimEvidence[];
  unmatched: SourceType[];
}

export interface StanceSummary {
  supports: number;
  contradicts: number;
  inconclusive: number;
}

/** Stance of a Source on a specific claim, resolved by the `claim_index` the investigator attaches to each `statement`. */
export function stanceForClaim(
  source: SourceType,
  claimIndex: number
): string | null | undefined {
  return source.statements?.find(
    statement => statement.claim_index === claimIndex
  )?.stance;
}

/** Group the Sources under the claims they support by `claim_index`, listing one under each of its claims and the rest in `unmatched`. */
export function groupSourcesByClaim(
  claims: ClaimType[],
  sources: SourceType[]
): GroupedEvidence {
  const groups: ClaimEvidence[] = claims.map(claim => ({ claim, sources: [] }));
  const unmatched: SourceType[] = [];

  for (const source of sources) {
    const matchedIndices = new Set<number>();
    for (const statement of source.statements ?? []) {
      const index = statement.claim_index;
      // An out-of-range index has no claim to nest the Source under.
      if (index >= 0 && index < groups.length) matchedIndices.add(index);
    }

    if (matchedIndices.size === 0) {
      unmatched.push(source);
    } else {
      for (const index of matchedIndices) groups[index].sources.push(source);
    }
  }

  return { groups, unmatched };
}

/** Count the Stances of the Sources linked to a claim, for the row's "for / against" summary. */
export function summarizeStances(
  claimIndex: number,
  sources: SourceType[]
): StanceSummary {
  const summary: StanceSummary = {
    supports: 0,
    contradicts: 0,
    inconclusive: 0,
  };

  for (const source of sources) {
    const stance = stanceForClaim(source, claimIndex);
    if (stance === 'supports') summary.supports += 1;
    else if (stance === 'contradicts') summary.contradicts += 1;
    else if (stance === 'inconclusive') summary.inconclusive += 1;
  }

  return summary;
}
