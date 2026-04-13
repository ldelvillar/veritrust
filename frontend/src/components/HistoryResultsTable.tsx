import Link from 'next/link';
import Spinner from '@/assets/Spinner';
import Arrow from '@/assets/Arrow';
import Warning from '@/assets/Warning';

export interface HistoryItem {
  id: string;
  user_id: string;
  source_type: 'text' | 'file' | 'url';
  input_text: string | null;
  input_url: string | null;
  label: string;
  confidence: number | string;
  explanation: string;
  created_at: string;
}

interface HistoryResultsTableProps {
  history: HistoryItem[];
  totalCount: number;
  isLoading: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
}

const getTitle = (item: HistoryItem): string => {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
};

const getSource = (item: HistoryItem): string => {
  if (item.source_type === 'file') return 'Carga de archivo';
  if (item.source_type === 'text') return 'Texto pegado';

  if (!item.input_url) return 'Enlace';

  try {
    return new URL(item.input_url).hostname;
  } catch {
    return 'Enlace';
  }
};

const getTypeLabel = (sourceType: HistoryItem['source_type']): string => {
  if (sourceType === 'file') return 'Archivo';
  if (sourceType === 'url') return 'Enlace';
  return 'Texto';
};

const getScore = (confidence: number | string): number => {
  const parsed = Number(confidence);
  if (Number.isNaN(parsed)) return 0;

  const normalized = parsed <= 1 ? parsed * 100 : parsed;
  return Math.max(0, Math.min(100, Math.round(normalized)));
};

const getScoreColor = (score: number): string => {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
};

export default function HistoryResultsTable({
  history,
  totalCount,
  isLoading,
  errorMessage,
  onRetry,
}: HistoryResultsTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
      <div className="hidden grid-cols-[2.2fr_0.8fr_0.9fr_1.2fr_0.9fr] gap-4 border-b border-border bg-slate-50 px-5 py-4 text-xs font-bold tracking-widest text-slate-400 uppercase md:grid">
        <span>Título del artículo</span>
        <span>Tipo</span>
        <span>Fecha de análisis</span>
        <span>Puntuación de credibilidad</span>
        <span className="text-right">Acción</span>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-3 px-5 py-12 text-sm font-semibold text-slate-500">
          <Spinner className="size-5 animate-spin text-primary" />
          Cargando análisis...
        </div>
      ) : errorMessage ? (
        <div className="px-5 py-12">
          <div className="mx-auto max-w-2xl rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-left">
            <div className="flex items-start gap-3">
              <Warning className="mt-0.5 size-5 shrink-0 text-red-500" />
              <div>
                <p className="text-sm font-bold text-red-700">
                  No se pudo cargar tu historial
                </p>
                <p className="mt-1 text-sm font-medium text-red-600">
                  {errorMessage}
                </p>
                {onRetry ? (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="mt-4 inline-flex items-center rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100"
                  >
                    Reintentar
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : history.length === 0 ? (
        <div className="px-5 py-12 text-center text-sm font-medium text-slate-500">
          Aún no tienes análisis o los resultados no coinciden con los filtros.
        </div>
      ) : (
        <ul>
          {history.map(item => {
            const score = getScore(item.confidence);
            const scoreColor = getScoreColor(score);

            return (
              <li
                key={item.id}
                className="border-b border-border px-4 py-4 last:border-b-0 md:grid md:grid-cols-[2.2fr_0.8fr_0.9fr_1.2fr_0.9fr] md:items-center md:gap-4 md:px-5"
              >
                <div className="min-w-0">
                  <p className="truncate text-base font-bold text-slate-800">
                    {getTitle(item)}
                  </p>
                  <p className="mt-1 truncate text-xs font-semibold text-slate-400">
                    Fuente: {getSource(item)}
                  </p>
                </div>

                <span className="mt-3 inline-flex w-fit items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 md:mt-0 md:rounded-none md:bg-transparent md:px-0 md:py-0 md:text-sm md:text-slate-600">
                  {getTypeLabel(item.source_type)}
                </span>

                <span className="mt-3 block text-xs font-semibold text-slate-500 md:mt-0 md:text-sm">
                  {new Date(item.created_at).toLocaleString('es-ES', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>

                <div className="mt-4 flex items-center gap-3 md:mt-0">
                  <div className="h-2 w-full rounded-full bg-slate-200 md:max-w-24">
                    <div
                      className={`h-full rounded-full ${scoreColor}`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <span className="text-sm font-black text-slate-700">
                    {score}/100
                  </span>
                </div>

                <Link
                  href={`/analisis/${item.id}`}
                  className="mt-4 inline-flex w-fit items-center gap-2 text-sm font-bold text-primary md:mt-0 md:justify-self-end"
                >
                  Ver informe
                  <Arrow className="size-4 rotate-270 text-primary" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex flex-col gap-4 border-t border-border bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <p className="text-xs font-semibold text-slate-400">
          {isLoading
            ? 'Cargando registros...'
            : errorMessage
              ? 'No se pudieron cargar los registros.'
              : `Mostrando ${history.length === 0 ? 0 : 1} a ${history.length} de ${totalCount} registros`}
        </p>

        <div className="flex w-full items-center justify-end gap-2 sm:w-auto">
          <button
            type="button"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-400"
          >
            ‹
          </button>
          <button
            type="button"
            className="size-8 rounded-lg bg-primary text-sm font-bold text-white"
          >
            1
          </button>
          <button
            type="button"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500"
          >
            2
          </button>
          <button
            type="button"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500"
          >
            3
          </button>
          <button
            type="button"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-400"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  );
}
