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

/**
 * Postura de una fuente sobre una afirmación concreta, resuelta por el
 * `claim_index` que el investigador adjunta a cada `statement`.
 */
export function stanceForClaim(
  source: SourceType,
  claimIndex: number
): string | null | undefined {
  return source.statements?.find(
    statement => statement.claim_index === claimIndex
  )?.stance;
}

/**
 * Agrupa las fuentes bajo la afirmación que respaldan, usando el `claim_index`
 * que el investigador adjunta a cada `statement`. Una fuente que respalda varias
 * afirmaciones aparece bajo todas ellas; las que no apuntan a ninguna afirmación
 * de la lista (o no traen `statements`) caen en `unmatched`.
 */
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
      // Un índice fuera de rango no tiene afirmación bajo la que anidar la fuente.
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

/**
 * Cuenta la postura de las fuentes ya enlazadas a una afirmación, para el
 * resumen "a favor / en contra" de la fila.
 */
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
