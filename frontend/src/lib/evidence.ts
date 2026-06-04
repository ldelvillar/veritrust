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

const normalize = (text: string): string => text.trim();

/**
 * Agrupa las fuentes bajo la afirmación que respaldan, usando el campo
 * `statements` que el investigador adjunta a cada fuente. Una fuente que
 * respalda varias afirmaciones aparece bajo todas ellas; las que no encajan en
 * ninguna (o sin `statements`) caen en `unmatched`.
 */
export function groupSourcesByClaim(
  claims: ClaimType[],
  sources: SourceType[]
): GroupedEvidence {
  const groups: ClaimEvidence[] = claims.map(claim => ({ claim, sources: [] }));

  // Primer índice gana ante textos de afirmación duplicados.
  const indexByText = new Map<string, number>();
  claims.forEach((claim, index) => {
    const key = normalize(claim.text);
    if (!indexByText.has(key)) indexByText.set(key, index);
  });

  const unmatched: SourceType[] = [];

  for (const source of sources) {
    const matchedIndices = new Set<number>();
    for (const statement of source.statements ?? []) {
      if (!statement) continue;
      const index = indexByText.get(normalize(statement));
      if (index !== undefined) matchedIndices.add(index);
    }

    if (matchedIndices.size === 0) {
      unmatched.push(source);
    } else {
      for (const index of matchedIndices) groups[index].sources.push(source);
    }
  }

  return { groups, unmatched };
}
