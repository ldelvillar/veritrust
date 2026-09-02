'use client';

import CheckIcon from '@/assets/Check';
import TrashIcon from '@/assets/Trash';
import WarningIcon from '@/assets/Warning';

interface DangerZoneCardProps {
  totalCount: number;
  deletedCount: number | null;
  onRequestDelete: () => void;
}

const numberFormatter = new Intl.NumberFormat('es-ES');

export default function DangerZoneCard({
  totalCount,
  deletedCount,
  onRequestDelete,
}: DangerZoneCardProps) {
  const isEmpty = totalCount === 0;
  const justDeleted = deletedCount !== null;

  return (
    <section
      aria-labelledby="cuenta-danger-title"
      className="rounded-2xl border border-danger/30 bg-[linear-gradient(180deg,var(--color-danger-soft),#fff_120px)] p-6 shadow-sm md:p-7"
    >
      <div className="flex items-start gap-3.5">
        <span
          aria-hidden
          className="grid size-10 shrink-0 place-items-center rounded-xl bg-danger-soft text-danger-ink"
        >
          <WarningIcon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2
            id="cuenta-danger-title"
            className="text-lg font-bold tracking-tight text-ink"
          >
            Zona de peligro
          </h2>
          <p className="mt-1 text-sm font-medium text-muted">
            Elimina permanentemente <strong className="text-body">todos</strong>{' '}
            tus análisis y sus informes. Esta acción es irreversible y no afecta
            al resto de tu cuenta.
          </p>
        </div>
      </div>

      <div className="mt-5 border-t border-danger/20 pt-5">
        {justDeleted ? (
          <p
            role="status"
            className="mb-4 flex items-start gap-2 rounded-xl bg-success-soft px-3.5 py-3 text-[13px] font-semibold text-success-ink"
          >
            <CheckIcon className="mt-px size-4 shrink-0" aria-hidden />
            Se han eliminado {numberFormatter.format(deletedCount)} análisis. Tu
            actividad está ahora vacía.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
          <p className="flex min-w-50 flex-1 items-start gap-2 text-xs font-medium text-muted">
            <TrashIcon
              className="mt-px size-4 shrink-0 text-faint"
              aria-hidden
            />
            {isEmpty
              ? 'No tienes actividad que eliminar.'
              : `Se eliminarán ${numberFormatter.format(totalCount)} análisis de forma permanente.`}
          </p>
          <button
            type="button"
            onClick={onRequestDelete}
            disabled={isEmpty}
            aria-haspopup="dialog"
            className="inline-flex items-center gap-2 rounded-xl bg-danger px-4 py-2.5 text-sm font-bold text-white shadow-[0_6px_16px_var(--tw-shadow-color)] shadow-danger/25 transition hover:bg-danger-ink focus-visible:ring-2 focus-visible:ring-danger/40 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            <TrashIcon className="size-4" aria-hidden />
            Eliminar toda mi actividad
            {!isEmpty ? (
              <span className="ml-0.5 rounded-full bg-white/20 px-2 py-px text-[11.5px] font-extrabold">
                {numberFormatter.format(totalCount)}
              </span>
            ) : null}
          </button>
        </div>
      </div>
    </section>
  );
}
