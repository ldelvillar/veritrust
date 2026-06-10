import Link from 'next/link';
import Spinner from '@/assets/Spinner';
import Arrow from '@/assets/Arrow';
import Warning from '@/assets/Warning';
import Trash from '@/assets/Trash';
import Magnifier from '@/assets/Magnifier';
import FunnelIcon from '@/assets/Funnel';
import type { paths } from '@/types/api';

type HistoryItem =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface HistoryResultsTableProps {
  history: HistoryItem[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
  isLoading: boolean;
  errorMessage?: string | null;
  onRetry?: () => void;
  onPageChange: (page: number) => void;
  onDelete: (item: HistoryItem) => void;
  deletingId?: string | null;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
}

const getTitle = (item: HistoryItem): string => {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.source_type === 'file' && item.file_filename)
    return item.file_filename;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
};

const getSource = (item: HistoryItem): string => {
  if (item.source_type === 'file')
    return item.file_filename ?? 'Carga de archivo';
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

const VERDICT_BADGES: Record<
  HistoryItem['verdict'],
  { text: string; className: string }
> = {
  fake: { text: 'Falsa', className: 'bg-red-50 text-red-700' },
  real: { text: 'Verdadera', className: 'bg-emerald-50 text-emerald-700' },
  uncertain: { text: 'Incierta', className: 'bg-amber-50 text-amber-700' },
};

const getScoreColor = (score: number): string => {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
};

const getVisiblePages = (
  currentPage: number,
  totalPages: number,
  maxVisible: number = 5
): number[] => {
  if (totalPages <= maxVisible) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const half = Math.floor(maxVisible / 2);
  let start = Math.max(1, currentPage - half);
  const end = Math.min(totalPages, start + maxVisible - 1);

  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }

  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
};

export default function HistoryResultsTable({
  history,
  totalCount,
  currentPage,
  pageSize,
  isLoading,
  errorMessage,
  onRetry,
  onPageChange,
  onDelete,
  deletingId,
  hasActiveFilters,
  onClearFilters,
}: HistoryResultsTableProps) {
  // Estado vacío dedicado: distingue primer uso (sin análisis) de filtros sin
  // coincidencias, sin la cabecera ni la paginación de la tabla.
  if (!isLoading && !errorMessage && history.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-white shadow-sm">
        <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <div className="flex size-14 items-center justify-center rounded-2xl bg-[#eeebfc] text-[#6356e6]">
            {hasActiveFilters ? (
              <FunnelIcon className="size-7" />
            ) : (
              <Magnifier className="size-7" />
            )}
          </div>
          <h2 className="mt-5 text-xl font-bold tracking-tight text-slate-900">
            {hasActiveFilters
              ? 'Sin resultados para estos filtros'
              : 'Aún no has analizado nada'}
          </h2>
          <p className="mt-2 max-w-sm text-sm font-medium text-slate-500">
            {hasActiveFilters
              ? 'Ningún análisis coincide con la búsqueda o los filtros aplicados. Prueba a ajustarlos o límpialos para ver todo tu historial.'
              : 'Cuando verifiques tu primer contenido médico, tus informes aparecerán aquí para que puedas consultarlos y gestionarlos.'}
          </p>
          {hasActiveFilters ? (
            <button
              type="button"
              onClick={onClearFilters}
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:border-primary hover:text-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
            >
              Limpiar filtros
            </button>
          ) : (
            <Link
              href="/app/analisis"
              className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_rgba(99,86,230,.32)] transition hover:bg-[#5446dc] focus:ring-4 focus:ring-primary/20 focus:outline-none"
            >
              Analizar contenido
            </Link>
          )}
        </div>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const safeCurrentPage = Math.min(Math.max(currentPage, 1), totalPages);
  const startRecord =
    totalCount === 0 ? 0 : (safeCurrentPage - 1) * pageSize + 1;
  const endRecord =
    totalCount === 0 ? 0 : Math.min(safeCurrentPage * pageSize, totalCount);
  const visiblePages = getVisiblePages(safeCurrentPage, totalPages);
  const isPaginationDisabled =
    isLoading || Boolean(errorMessage) || totalCount === 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
      <div className="hidden grid-cols-[2.2fr_0.8fr_0.9fr_1.2fr_0.9fr] gap-4 border-b border-border bg-slate-50 px-5 py-4 text-xs font-bold tracking-widest text-slate-400 uppercase md:grid">
        <span>Título del artículo</span>
        <span>Tipo</span>
        <span>Fecha de análisis</span>
        <span>Credibilidad</span>
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
      ) : (
        <ul>
          {history.map(item => {
            const credibility = item.credibility ?? null;
            const verdict = VERDICT_BADGES[item.verdict];

            return (
              <li
                key={item.analysis_id}
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

                <div className="mt-4 flex flex-col items-start gap-2 md:mt-0">
                  <span
                    className={`inline-flex w-fit items-center rounded-md px-2 py-0.5 text-[11px] font-bold tracking-wide uppercase ${verdict.className}`}
                  >
                    {verdict.text}
                  </span>
                  <div className="flex w-full items-center gap-3">
                    {credibility === null ? (
                      <span className="text-sm font-semibold text-slate-400">
                        Sin puntuación
                      </span>
                    ) : (
                      <>
                        <div className="h-2 w-full rounded-full bg-slate-200 md:max-w-24">
                          <div
                            className={`h-full rounded-full ${getScoreColor(credibility)}`}
                            style={{ width: `${credibility}%` }}
                          />
                        </div>
                        <span className="text-sm font-black text-slate-700">
                          {credibility}/100
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-3 md:mt-0 md:justify-self-end">
                  <Link
                    href={`/app/analisis/${item.analysis_id}`}
                    className="inline-flex w-fit items-center gap-2 text-sm font-bold text-primary"
                  >
                    Ver informe
                    <Arrow className="size-4 rotate-270 text-primary" />
                  </Link>
                  <button
                    type="button"
                    onClick={() => onDelete(item)}
                    disabled={deletingId === item.analysis_id}
                    aria-label="Eliminar análisis"
                    className="inline-flex size-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-red-50 hover:text-red-600 focus:ring-2 focus:ring-red-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {deletingId === item.analysis_id ? (
                      <Spinner className="size-4 animate-spin text-red-500" />
                    ) : (
                      <Trash className="size-4" />
                    )}
                  </button>
                </div>
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
              : `Mostrando ${startRecord} a ${endRecord} de ${totalCount} registros`}
        </p>

        <div className="flex w-full items-center justify-end gap-2 sm:w-auto">
          <button
            type="button"
            onClick={() => onPageChange(safeCurrentPage - 1)}
            disabled={isPaginationDisabled || safeCurrentPage === 1}
            aria-label="Página anterior"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500 transition disabled:cursor-not-allowed disabled:text-slate-300"
          >
            ‹
          </button>

          {visiblePages.map(page => {
            const isActive = page === safeCurrentPage;

            return (
              <button
                key={page}
                type="button"
                onClick={() => onPageChange(page)}
                disabled={isPaginationDisabled}
                aria-current={isActive ? 'page' : undefined}
                className={`size-8 rounded-lg text-sm font-bold transition ${
                  isActive
                    ? 'bg-primary text-white'
                    : 'border border-border bg-white text-slate-500 hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-300'
                }`}
              >
                {page}
              </button>
            );
          })}

          <button
            type="button"
            onClick={() => onPageChange(safeCurrentPage + 1)}
            disabled={isPaginationDisabled || safeCurrentPage === totalPages}
            aria-label="Página siguiente"
            className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500 transition disabled:cursor-not-allowed disabled:text-slate-300"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  );
}
