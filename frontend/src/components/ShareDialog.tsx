'use client';

import { useEffect, useId, useRef, useState } from 'react';
import Spinner from '@/assets/Spinner';
import Check from '@/assets/Check';
import LinkIcon from '@/assets/Link';

interface ShareDialogProps {
  open: boolean;
  shareUrl: string | null;
  isSharing: boolean;
  error: string | null;
  onCreate: () => void;
  onRemove: () => void;
  onClose: () => void;
}

export default function ShareDialog({
  open,
  shareUrl,
  isSharing,
  error,
  onCreate,
  onRemove,
  onClose,
}: ShareDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const [copied, setCopied] = useState(false);

  // Cierra con Escape mientras el diálogo está abierto.
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isSharing) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, isSharing, onClose]);

  // Lleva el foco al botón de cerrar al abrir.
  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  // Restablece «copiado» cuando cambia el enlace (revocar y volver a crear).
  const [trackedUrl, setTrackedUrl] = useState(shareUrl);
  if (trackedUrl !== shareUrl) {
    setTrackedUrl(shareUrl);
    setCopied(false);
  }

  if (!open) return null;

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onClick={() => {
        if (!isSharing) onClose();
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
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
            <LinkIcon className="size-5 text-primary" />
          </span>
          <div className="min-w-0">
            <h2
              id={titleId}
              className="text-lg font-black tracking-tight text-slate-900"
            >
              Compartir informe
            </h2>
            <p
              id={descriptionId}
              className="mt-1 text-sm font-medium text-slate-500"
            >
              Cualquiera con el enlace podrá ver este informe en modo lectura,
              sin acceder a tu cuenta. Puedes desactivarlo cuando quieras.
            </p>
          </div>
        </div>

        {shareUrl ? (
          <div className="mt-5">
            <label
              htmlFor={`${titleId}-url`}
              className="text-xs font-bold tracking-wide text-slate-500 uppercase"
            >
              Enlace público
            </label>
            <div className="mt-1.5 flex gap-2">
              <input
                id={`${titleId}-url`}
                type="text"
                readOnly
                value={shareUrl}
                onFocus={event => event.target.select()}
                className="min-w-0 flex-1 rounded-xl border border-border bg-slate-50 px-3 py-2.5 text-sm text-slate-700 focus:border-primary focus:outline-none"
              />
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-2 focus:ring-primary/20 focus:outline-none"
              >
                {copied ? (
                  <>
                    <Check className="size-4" />
                    Copiado
                  </>
                ) : (
                  'Copiar'
                )}
              </button>
            </div>
          </div>
        ) : null}

        {error ? (
          <p role="alert" className="mt-4 text-sm font-semibold text-red-600">
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            disabled={isSharing}
            className="rounded-xl border border-border bg-white px-4 py-2 text-sm font-bold text-slate-600 transition hover:bg-slate-50 focus:ring-2 focus:ring-slate-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cerrar
          </button>
          {shareUrl ? (
            <button
              type="button"
              onClick={onRemove}
              disabled={isSharing}
              aria-busy={isSharing}
              className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-bold text-red-600 transition hover:bg-red-50 focus:ring-2 focus:ring-red-200 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSharing ? (
                <Spinner className="size-4 animate-spin text-red-500" />
              ) : null}
              Desactivar enlace
            </button>
          ) : (
            <button
              type="button"
              onClick={onCreate}
              disabled={isSharing}
              aria-busy={isSharing}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSharing ? (
                <Spinner className="size-4 animate-spin text-white" />
              ) : null}
              Crear enlace público
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
