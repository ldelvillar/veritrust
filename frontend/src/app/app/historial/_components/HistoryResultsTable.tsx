import Link from 'next/link';
import Spinner from '@/assets/Spinner';
import ArrowRightIcon from '@/assets/ArrowRight';
import Warning from '@/assets/Warning';
import Trash from '@/assets/Trash';
import Magnifier from '@/assets/Magnifier';
import FunnelIcon from '@/assets/Funnel';
import TypeIcon from '@/assets/Type';
import LinkIcon from '@/assets/Link';
import DocumentIcon from '@/assets/Document';
import GlobeIcon from '@/assets/Globe';
import RefreshIcon from '@/assets/Refresh';
import BookIcon from '@/assets/Book';
import Button from '@/components/Button';
import {
  formatCoverage,
  VERDICT_LABEL,
} from '@/components/analysis-result/format';
import HistoryStatePanel from './HistoryStatePanel';
import { SkeletonRows } from './HistorySkeleton';
import type { paths } from '@/types/api';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
type HistoryItem = HistoryPayload['items'][number];

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

type Tone = 'ok' | 'warn' | 'bad';

const TONE_CONFIG = {
  ok: {
    rail: 'linear-gradient(180deg,var(--color-verdict-real-g1),var(--color-verdict-real-g2))',
    ring: 'var(--color-verdict-real)',
    textColor: 'var(--color-verdict-real-ink)',
    bgColor: 'var(--color-verdict-real-soft)',
    label: VERDICT_LABEL.real,
  },
  warn: {
    rail: 'linear-gradient(180deg,var(--color-verdict-uncertain-g1),var(--color-verdict-uncertain-g2))',
    ring: 'var(--color-verdict-uncertain)',
    textColor: 'var(--color-verdict-uncertain-ink)',
    bgColor: 'var(--color-verdict-uncertain-soft)',
    label: VERDICT_LABEL.uncertain,
  },
  bad: {
    rail: 'linear-gradient(180deg,var(--color-verdict-fake-g1),var(--color-verdict-fake-g2))',
    ring: 'var(--color-verdict-fake)',
    textColor: 'var(--color-verdict-fake-ink)',
    bgColor: 'var(--color-verdict-fake-soft)',
    label: VERDICT_LABEL.fake,
  },
} satisfies Record<Tone, object>;

const TYPE_META = {
  text: { label: 'Texto', tint: '#eeebfc', color: '#6356e6', Icon: TypeIcon },
  url: { label: 'Enlace', tint: '#e4f1fc', color: '#2c97e8', Icon: LinkIcon },
  file: {
    label: 'Archivo',
    tint: '#def4ea',
    color: '#13b877',
    Icon: DocumentIcon,
  },
} as const;

// El worker reporta la etapa real; aquí la traducimos a una etiqueta compacta.
const STAGE_LABEL: Record<string, string> = {
  preparing: 'Preparando el contenido',
  extractor: 'Extrayendo afirmaciones',
  translator: 'Traduciendo al inglés clínico',
  investigator: 'Buscando evidencia',
  health_expert: 'Evaluando y redactando',
};

const STATUS_BADGES = {
  pending: { text: 'En curso', textColor: '#5446dc', bgColor: '#eeebfc' },
  failed_no_claims: {
    text: 'Sin afirmaciones',
    textColor: '#7e7f99',
    bgColor: '#f4f2fd',
  },
  failed: { text: 'Fallido', textColor: '#c23552', bgColor: '#fbe4e8' },
} as const;

function toneFromItem(item: HistoryItem): Tone | null {
  if (item.status !== 'done') return null;
  const s = item.credibility;
  if (s === null || s === undefined) return null;
  if (s >= 70) return 'ok';
  if (s >= 45) return 'warn';
  return 'bad';
}

function getTitle(item: HistoryItem): string {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.source_type === 'file' && item.file_filename)
    return item.file_filename;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
}

function getSource(item: HistoryItem): string {
  if (item.source_type === 'file')
    return item.file_filename ?? 'Carga de archivo';
  if (item.source_type === 'text') return 'Texto pegado';
  if (!item.input_url) return 'Enlace';
  try {
    return new URL(item.input_url).hostname;
  } catch {
    return 'Enlace';
  }
}

function CredibilityGauge({ score, tone }: { score: number; tone: Tone }) {
  const r = 19;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score / 100);
  const cfg = TONE_CONFIG[tone];
  return (
    <div
      className="relative size-12.5 shrink-0"
      aria-label={`Credibilidad: ${score}/100`}
    >
      <svg viewBox="0 0 48 48" className="size-full" aria-hidden>
        <circle
          cx="24"
          cy="24"
          r={r}
          fill="none"
          stroke="#ece9f7"
          strokeWidth="4.5"
        />
        <circle
          cx="24"
          cy="24"
          r={r}
          fill="none"
          stroke={cfg.ring}
          strokeWidth="4.5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 24 24)"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-[13px] font-bold tabular-nums"
        style={{ color: cfg.textColor }}
      >
        {score}
      </span>
    </div>
  );
}

function GaugePlaceholder({ status }: { status: HistoryItem['status'] }) {
  return (
    <div className="relative size-12.5 shrink-0">
      <svg viewBox="0 0 48 48" className="size-full" aria-hidden>
        <circle
          cx="24"
          cy="24"
          r={19}
          fill="none"
          stroke="#ece9f7"
          strokeWidth="4.5"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center">
        {status === 'pending' ? (
          <Spinner className="size-4 animate-spin text-primary" />
        ) : (
          <span className="text-[11px] font-bold text-faint">—</span>
        )}
      </span>
    </div>
  );
}

function getVisiblePages(current: number, total: number, max = 5): number[] {
  if (total <= max) return Array.from({ length: total }, (_, i) => i + 1);
  const half = Math.floor(max / 2);
  let start = Math.max(1, current - half);
  const end = Math.min(total, start + max - 1);
  if (end - start + 1 < max) start = Math.max(1, end - max + 1);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
}

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
  if (!isLoading && !errorMessage && history.length === 0) {
    return (
      <div className="rounded-[18px] border border-line bg-white shadow-sm">
        <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
          <div className="flex size-15 items-center justify-center rounded-2xl bg-[#eeebfc] text-[#6356e6]">
            {hasActiveFilters ? (
              <FunnelIcon className="size-7" />
            ) : (
              <Magnifier className="size-7" />
            )}
          </div>
          <h3 className="mt-4.5 text-lg font-bold tracking-tight text-ink">
            {hasActiveFilters ? 'Sin resultados' : 'Aún no has analizado nada'}
          </h3>
          <p className="mt-1.5 max-w-sm text-sm font-medium text-muted">
            {hasActiveFilters
              ? 'No hay análisis que coincidan con los filtros seleccionados.'
              : 'Cuando verifiques tu primer contenido médico, tus informes aparecerán aquí para que puedas consultarlos y gestionarlos.'}
          </p>
          {hasActiveFilters ? (
            <Button variant="soft" onClick={onClearFilters} className="mt-4.5">
              Limpiar filtros
            </Button>
          ) : (
            <Button href="/app/analisis" className="mt-4.5">
              Analizar contenido
            </Button>
          )}
        </div>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const safePage = Math.min(Math.max(currentPage, 1), totalPages);
  const startRecord = totalCount === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const endRecord =
    totalCount === 0 ? 0 : Math.min(safePage * pageSize, totalCount);
  const visiblePages = getVisiblePages(safePage, totalPages);
  const paginationDisabled =
    isLoading || Boolean(errorMessage) || totalCount === 0;

  return (
    <div className="flex flex-col gap-3">
      {isLoading ? (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2.75 text-[13px] font-semibold text-muted">
            <span
              className="size-4.5 shrink-0 animate-spin rounded-full border-[2.5px] border-primary/20 border-t-primary"
              aria-hidden
            />
            <span>Cargando análisis…</span>
          </div>
          <SkeletonRows count={6} />
        </div>
      ) : errorMessage ? (
        <HistoryStatePanel
          variant="red"
          icon={<Warning className="size-9.5" />}
          eyebrow="Error de conexión"
          title="No se pudo cargar tu historial"
          lead={
            <>
              No hemos podido recuperar tus informes guardados en este momento.
              Tus análisis siguen <b className="font-bold text-body">a salvo</b>
              ; solo es un problema temporal de conexión con el servidor.
            </>
          }
          actions={
            onRetry && (
              <Button onClick={onRetry} size="lg">
                <RefreshIcon className="size-4.5" aria-hidden />
                Reintentar
              </Button>
            )
          }
          footer={
            <div className="relative mt-8 inline-flex max-w-full items-center gap-2.5 rounded-[10px] border border-line bg-surface-subtle px-3.5 py-2.5 font-mono text-xs text-faint">
              <span
                className="size-1.75 shrink-0 rounded-full bg-[#e0556b]"
                aria-hidden
              />
              <span className="truncate">{errorMessage}</span>
            </div>
          }
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {history.map(item => {
            const tone = toneFromItem(item);
            const toneCfg = tone ? TONE_CONFIG[tone] : null;
            const typeMeta =
              TYPE_META[item.source_type as keyof typeof TYPE_META] ??
              TYPE_META.text;
            const { Icon: SourceIcon } = typeMeta;
            const credibility = item.credibility ?? null;
            const isDeleting = deletingId === item.analysis_id;
            const stageLabel =
              item.status === 'pending' && item.stage
                ? (STAGE_LABEL[item.stage] ?? null)
                : null;

            const railStyle = toneCfg
              ? toneCfg.rail
              : item.status === 'pending'
                ? 'linear-gradient(180deg,#9d96ef,#7b72e3)'
                : 'linear-gradient(180deg,#c5c3d6,#b0adc4)';

            let statusBadgeCfg: {
              text: string;
              textColor: string;
              bgColor: string;
            } | null = null;
            let detailLabel = 'Ver informe';
            if (item.status === 'pending') {
              statusBadgeCfg = STATUS_BADGES.pending;
              detailLabel = 'Ver estado';
            } else if (item.status === 'failed') {
              statusBadgeCfg =
                item.error_code === 'NO_MEDICAL_CLAIMS'
                  ? STATUS_BADGES.failed_no_claims
                  : STATUS_BADGES.failed;
              detailLabel = 'Ver detalle';
            }

            const badgeText = statusBadgeCfg
              ? statusBadgeCfg.text
              : (toneCfg?.label ?? VERDICT_LABEL.uncertain);
            const badgeTextColor = statusBadgeCfg
              ? statusBadgeCfg.textColor
              : (toneCfg?.textColor ?? '#7e7f99');
            const badgeBgColor = statusBadgeCfg
              ? statusBadgeCfg.bgColor
              : (toneCfg?.bgColor ?? '#f4f2fd');

            const formattedDate = new Date(item.created_at).toLocaleString(
              'es-ES',
              {
                day: 'numeric',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              }
            );

            return (
              <li
                key={item.analysis_id}
                className="group relative flex flex-wrap items-center gap-3.5 overflow-hidden rounded-2xl border border-line bg-white py-4 pr-4 pl-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md sm:flex-nowrap sm:gap-4.5 sm:py-4.5 sm:pr-5.5 sm:pl-6"
              >
                {/* Left tone rail */}
                <div
                  className="absolute inset-y-0 left-0 w-1"
                  style={{ background: railStyle }}
                  aria-hidden
                />

                {/* Credibility gauge */}
                {tone !== null && credibility !== null ? (
                  <CredibilityGauge score={credibility} tone={tone} />
                ) : (
                  <GaugePlaceholder status={item.status} />
                )}

                {/* Main content */}
                <div className="min-w-35 flex-1">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span
                      className="flex size-5.5 shrink-0 items-center justify-center rounded-[7px]"
                      style={{
                        background: typeMeta.tint,
                        color: typeMeta.color,
                      }}
                    >
                      <SourceIcon width={13} height={13} />
                    </span>
                    <span className="text-xs font-bold text-body">
                      {typeMeta.label}
                    </span>
                    <span
                      className="size-0.75 rounded-full bg-faint"
                      aria-hidden
                    />
                    <span className="text-[12.5px] font-semibold whitespace-nowrap text-faint">
                      {formattedDate}
                    </span>
                    {item.status === 'done' &&
                      item.evidence_coverage != null && (
                        <>
                          <span
                            className="size-0.75 rounded-full bg-faint"
                            aria-hidden
                          />
                          <span className="inline-flex items-center gap-1 text-[12.5px] font-semibold whitespace-nowrap text-muted">
                            <BookIcon className="size-3.25" />
                            {formatCoverage(item.evidence_coverage)} cobertura
                          </span>
                        </>
                      )}
                    {item.share_token && (
                      <span
                        className="inline-flex items-center gap-1 rounded-full bg-[#eeebfc] px-2 py-0.5 text-[10.5px] font-bold tracking-[.03em] text-primary uppercase"
                        title="Este informe tiene un enlace público activo"
                      >
                        <GlobeIcon className="size-3" />
                        Compartido
                      </span>
                    )}
                  </div>
                  <p className="text-[15px] font-semibold text-pretty text-ink transition-colors group-hover:text-primary sm:truncate sm:text-left">
                    {getTitle(item)}
                  </p>
                  <p className="mt-1 text-[12.5px] font-semibold text-muted sm:truncate">
                    Fuente:{' '}
                    <b className="font-bold text-body">{getSource(item)}</b>
                  </p>
                  {stageLabel && (
                    <p className="mt-1 flex items-center gap-1.5 text-[12.5px] font-semibold text-primary">
                      <Spinner className="size-3 shrink-0 animate-spin" />
                      {stageLabel}
                    </p>
                  )}
                </div>

                {/* Right column */}
                <div className="flex flex-[1_1_100%] items-center justify-between gap-2.5 border-t border-line pt-3.5 sm:flex-none sm:gap-4.5 sm:border-0 sm:pt-0">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-bold tracking-[.04em] whitespace-nowrap uppercase"
                    style={{ color: badgeTextColor, background: badgeBgColor }}
                  >
                    <span
                      className="size-1.75 rounded-full bg-current"
                      aria-hidden
                    />
                    {badgeText}
                  </span>

                  <div className="flex items-center gap-1">
                    <Link
                      href={`/app/analisis/${item.analysis_id}`}
                      className="inline-flex items-center gap-1.5 rounded-[9px] bg-primary/8 px-3 py-2 text-[13px] font-semibold whitespace-nowrap text-primary transition hover:bg-primary/15 sm:bg-transparent sm:hover:bg-primary/8"
                    >
                      {detailLabel}
                      <ArrowRightIcon className="size-3.75 transition-transform group-hover:translate-x-0.5" />
                    </Link>
                    <button
                      type="button"
                      onClick={() => onDelete(item)}
                      disabled={isDeleting}
                      aria-label="Eliminar análisis"
                      className="flex size-8.5 items-center justify-center rounded-[9px] text-faint transition hover:bg-[#fbe4e8] hover:text-[#c23552] focus:ring-2 focus:ring-red-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isDeleting ? (
                        <Spinner className="size-4 animate-spin text-red-500" />
                      ) : (
                        <Trash className="size-4" />
                      )}
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Pagination footer */}
      {!isLoading && !errorMessage && (
        <div className="mt-1 flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[13px] font-semibold text-muted">
            {`Mostrando ${startRecord}–${endRecord} de ${totalCount} registros`}
          </p>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => onPageChange(safePage - 1)}
              disabled={paginationDisabled || safePage === 1}
              aria-label="Página anterior"
              className="flex size-9.5 items-center justify-center rounded-[10px] border border-line-strong bg-white text-sm font-bold text-muted transition hover:enabled:border-primary hover:enabled:text-primary disabled:cursor-not-allowed disabled:opacity-45"
            >
              ‹
            </button>

            {visiblePages.map(page => {
              const isActive = page === safePage;
              return (
                <button
                  key={page}
                  type="button"
                  onClick={() => onPageChange(page)}
                  disabled={paginationDisabled}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex size-9.5 items-center justify-center rounded-[10px] text-[13.5px] font-bold transition ${
                    isActive
                      ? 'bg-primary text-white shadow-[0_6px_16px_rgba(99,86,230,.3)]'
                      : 'border border-line-strong bg-white text-muted hover:border-primary hover:text-primary disabled:cursor-not-allowed disabled:opacity-45'
                  }`}
                >
                  {page}
                </button>
              );
            })}

            <button
              type="button"
              onClick={() => onPageChange(safePage + 1)}
              disabled={paginationDisabled || safePage === totalPages}
              aria-label="Página siguiente"
              className="flex size-9.5 items-center justify-center rounded-[10px] border border-line-strong bg-white text-sm font-bold text-muted transition hover:enabled:border-primary hover:enabled:text-primary disabled:cursor-not-allowed disabled:opacity-45"
            >
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
