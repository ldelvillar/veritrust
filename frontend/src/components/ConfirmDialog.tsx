'use client';

import { useEffect, useId, useRef } from 'react';
import Spinner from '@/assets/Spinner';
import Warning from '@/assets/Warning';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isConfirming?: boolean;
  errorMessage?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Eliminar',
  cancelLabel = 'Cancelar',
  isConfirming = false,
  errorMessage = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Cierra con Escape mientras el diálogo está abierto.
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isConfirming) onCancel();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, isConfirming, onCancel]);

  // Lleva el foco al botón de cancelar al abrir.
  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
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
            <Warning className="size-5 text-red-600" />
          </span>
          <div className="min-w-0">
            <h2
              id={titleId}
              className="text-lg font-black tracking-tight text-slate-900"
            >
              {title}
            </h2>
            <p
              id={descriptionId}
              className="mt-1 text-sm font-medium text-slate-500"
            >
              {description}
            </p>
          </div>
        </div>

        {errorMessage ? (
          <p role="alert" className="mt-4 text-sm font-semibold text-red-600">
            {errorMessage}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={isConfirming}
            className="rounded-xl border border-border bg-white px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-50 focus:ring-2 focus:ring-slate-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isConfirming}
            aria-busy={isConfirming}
            className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-red-700 focus:ring-2 focus:ring-red-300 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isConfirming ? (
              <Spinner className="size-4 animate-spin text-white" />
            ) : null}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
