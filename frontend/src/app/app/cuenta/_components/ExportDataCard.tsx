'use client';

import DownloadIcon from '@/assets/Download';
import ShieldIcon from '@/assets/Shield';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';

interface ExportDataCardProps {
  totalCount: number;
  isExporting: boolean;
  errorMessage: string | null;
  onExport: () => void;
}

export default function ExportDataCard({
  totalCount,
  isExporting,
  errorMessage,
  onExport,
}: ExportDataCardProps) {
  const isEmpty = totalCount === 0;
  const isDisabled = isExporting || isEmpty;

  return (
    <section
      aria-labelledby="cuenta-export-title"
      className="rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] md:p-7"
    >
      <div className="flex items-start gap-3.5">
        <span
          aria-hidden
          className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#efedfc] text-primary"
        >
          <DownloadIcon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2
            id="cuenta-export-title"
            className="text-lg font-bold tracking-tight text-ink"
          >
            Exportar tus datos
          </h2>
          <p className="mt-1 text-sm font-medium text-muted">
            Descarga todo tu historial de análisis en un archivo CSV: cada
            veredicto, su puntuación de credibilidad, las fuentes consultadas y
            la fecha.
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <p className="flex min-w-50 flex-1 items-start gap-2 text-xs font-medium text-muted">
          <ShieldIcon
            className="mt-px size-4 shrink-0 text-faint"
            aria-hidden
          />
          El archivo se genera al momento y se descarga en tu dispositivo. No se
          comparte con terceros.
        </p>
        <button
          type="button"
          onClick={onExport}
          disabled={isDisabled}
          aria-busy={isExporting}
          className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-primary/8 px-4 py-2.5 text-sm font-bold text-primary transition hover:bg-primary/15 focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isExporting ? (
            <Spinner className="size-4 animate-spin text-primary" aria-hidden />
          ) : (
            <DownloadIcon className="size-4" aria-hidden />
          )}
          {isExporting ? 'Exportando…' : 'Exportar todos mis datos'}
        </button>
      </div>

      {isEmpty ? (
        <p className="mt-3.5 text-[13px] font-semibold text-muted">
          Aún no tienes análisis que exportar. Verifica tu primer contenido para
          empezar.
        </p>
      ) : null}

      {errorMessage ? (
        <p
          role="alert"
          className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 px-3.5 py-3 text-[13px] font-semibold text-red-600"
        >
          <WarningIcon className="mt-px size-4 shrink-0" aria-hidden />
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}
