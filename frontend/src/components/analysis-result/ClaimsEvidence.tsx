import ListIcon from '@/assets/List';
import BookIcon from '@/assets/Book';
import { groupSourcesByClaim } from '@/lib/evidence';
import ClaimRow from './ClaimRow';
import SourcesCard from './SourcesCard';
import type { ClaimType, SourceType } from './types';

const FLAT_SOURCES_CAPTION =
  'Literatura biomédica recuperada de Europe PMC para respaldar el análisis. La confianza del veredicto se ajusta según cuántas afirmaciones encuentran respaldo en estas fuentes.';

export default function ClaimsEvidence({
  claims,
  sources,
}: {
  claims: ClaimType[];
  sources: SourceType[];
}) {
  const hasEvidence = sources.length > 0;

  // Caso defensivo: fuentes sin afirmaciones → lista plana, sin perder nada.
  if (claims.length === 0) {
    return hasEvidence ? (
      <SourcesCard
        sources={sources}
        title="Fuentes"
        caption={FLAT_SOURCES_CAPTION}
      />
    ) : null;
  }

  // Análisis antiguos (previos al investigador) no tienen fuentes: no decimos
  // "sin evidencia" porque nunca llegó a buscarse.
  if (!hasEvidence) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <ListIcon className="size-4.5 text-primary" />
          Afirmaciones detectadas
        </h3>
        <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
          Cada afirmación verificable se evalúa por separado con el modelo
          BioBERT.
        </p>
        {claims.map((claim, index) => (
          <ClaimRow
            key={index}
            claim={claim}
            sources={[]}
            showEvidence={false}
          />
        ))}
      </div>
    );
  }

  const { groups, unmatched } = groupSourcesByClaim(claims, sources);
  const backed = groups.filter(group => group.sources.length > 0).length;

  return (
    <>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <ListIcon className="size-4.5 text-primary" />
          Afirmaciones y evidencia
        </h3>
        <p className="mt-1 mb-3 text-[13px] leading-relaxed text-slate-500">
          Cada afirmación se evalúa con BioBERT y se enlaza con la literatura
          biomédica de Europe PMC que la respalda.
        </p>
        <p className="mb-4 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-[13px] font-semibold text-primary">
          <BookIcon className="size-4 shrink-0" />
          {backed} de {claims.length}{' '}
          {claims.length === 1
            ? 'afirmación respaldada'
            : 'afirmaciones respaldadas'}{' '}
          por literatura biomédica
        </p>
        {groups.map((group, index) => (
          <ClaimRow
            key={index}
            claim={group.claim}
            sources={group.sources}
            showEvidence
          />
        ))}
      </div>

      {unmatched.length > 0 && (
        <SourcesCard
          sources={unmatched}
          title="Otras fuentes relacionadas"
          caption="Fuentes recuperadas para el conjunto del texto que no se han asignado a una afirmación concreta."
        />
      )}
    </>
  );
}
