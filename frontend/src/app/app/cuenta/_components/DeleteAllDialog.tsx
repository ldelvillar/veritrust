'use client';

import { useEffect, useId, useRef, useState } from 'react';
import Spinner from '@/assets/Spinner';
import TrashIcon from '@/assets/Trash';
import WarningIcon from '@/assets/Warning';

interface DeleteAllDialogProps {
  open: boolean;
  count: number;
  isConfirming?: boolean;
  errorMessage?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

const CONFIRM_PHRASE = 'ELIMINAR';

export default function DeleteAllDialog(props: DeleteAllDialogProps) {
  if (!props.open) return null;
  return <DeleteAllDialogInner {...props} />;
}

function DeleteAllDialogInner({
  count,
  isConfirming = false,
  errorMessage = null,
  onConfirm,
  onCancel,
}: DeleteAllDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 40);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isConfirming) onCancel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isConfirming, onCancel]);

  const matches = value.trim() === CONFIRM_PHRASE;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4"
      onClick={() => {
        if (!isConfirming) onCancel();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onClick={event => event.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl"
      >
        <div className="flex items-start gap-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-red-100">
            <WarningIcon className="size-5 text-red-600" />
          </span>
          <div className="min-w-0">
            <h2
              id={titleId}
              className="text-lg font-black tracking-tight text-ink"
            >
              ¿Eliminar toda tu actividad?
            </h2>
            <p
              id={descriptionId}
              className="mt-1 text-sm font-medium text-muted"
            >
              Se borrarán permanentemente tus{' '}
              <strong className="text-body">
                {new Intl.NumberFormat('es-ES').format(count)} análisis
              </strong>{' '}
              y todos sus informes. Esta acción no se puede deshacer.
            </p>
          </div>
        </div>

        <label className="mt-5 block">
          <span className="mb-2 block text-[13px] font-bold text-body">
            Escribe{' '}
            <span className="font-extrabold tracking-wide text-red-600">
              {CONFIRM_PHRASE}
            </span>{' '}
            para confirmar
          </span>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={event => setValue(event.target.value)}
            disabled={isConfirming}
            autoComplete="off"
            spellCheck={false}
            aria-label={`Escribe ${CONFIRM_PHRASE} para confirmar la eliminación total`}
            placeholder={CONFIRM_PHRASE}
            className="w-full rounded-xl border border-line-strong bg-surface-subtle px-3.5 py-2.5 text-sm font-semibold tracking-wide text-ink transition outline-none placeholder:font-semibold placeholder:tracking-wide placeholder:text-faint focus:border-red-500 focus:bg-white focus:ring-4 focus:ring-red-500/15 disabled:opacity-50"
          />
        </label>

        {errorMessage ? (
          <p role="alert" className="mt-4 text-sm font-semibold text-red-600">
            {errorMessage}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isConfirming}
            className="rounded-xl border border-border bg-white px-4 py-2 text-sm font-bold text-body transition hover:bg-surface-subtle focus:ring-2 focus:ring-line focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isConfirming || !matches}
            aria-busy={isConfirming}
            className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-red-700 focus:ring-2 focus:ring-red-300 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isConfirming ? (
              <Spinner className="size-4 animate-spin text-white" />
            ) : (
              <TrashIcon className="size-4" aria-hidden />
            )}
            {isConfirming ? 'Eliminando…' : 'Eliminar todo'}
          </button>
        </div>
      </div>
    </div>
  );
}
