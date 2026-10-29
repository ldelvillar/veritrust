'use client';

import { useEffect, useId, useRef, useState } from 'react';
import Spinner from '@/assets/Spinner';
import Check from '@/assets/Check';
import LinkIcon from '@/assets/Link';
import Button from '@/components/Button';
import UpgradePrompt from '@/components/UpgradePrompt';

interface ShareDialogProps {
  open: boolean;
  shareUrl: string | null;
  isSharing: boolean;
  error: string | null;
  onCreate: () => void;
  onRemove: () => void;
  onClose: () => void;
  locked?: boolean;
}

export default function ShareDialog({
  open,
  shareUrl,
  isSharing,
  error,
  onCreate,
  onRemove,
  onClose,
  locked = false,
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4"
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
              className="text-lg font-black tracking-tight text-ink"
            >
              Compartir informe
            </h2>
            <p
              id={descriptionId}
              className="mt-1 text-sm font-medium text-muted"
            >
              Cualquiera con el enlace podrá ver este informe en modo lectura,
              sin acceder a tu cuenta. Puedes desactivarlo cuando quieras.
            </p>
          </div>
        </div>

        {/* Sin Pro el enlace existente responde 404, pero se puede desactivar; uno nuevo no se crea. */}
        {locked ? (
          shareUrl ? (
            <p className="mt-4 rounded-xl bg-warning-soft px-3.5 py-3 text-sm font-semibold text-warning-ink">
              Este informe tiene un enlace público que no funciona mientras no
              tengas el plan Pro. Vuelve a funcionar si te pasas a Pro, o puedes
              desactivarlo.
            </p>
          ) : (
            <UpgradePrompt variant="inline" className="mt-5">
              Los enlaces públicos son del plan Pro.
            </UpgradePrompt>
          )
        ) : shareUrl ? (
          <div className="mt-5">
            <label
              htmlFor={`${titleId}-url`}
              className="text-xs font-bold tracking-wide text-muted uppercase"
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
                className="min-w-0 flex-1 rounded-xl border border-border bg-surface-subtle px-3 py-2.5 text-sm text-body focus:border-primary focus:outline-none"
              />
              <Button onClick={handleCopy} className="shrink-0">
                {copied ? (
                  <>
                    <Check className="size-4" />
                    Copiado
                  </>
                ) : (
                  'Copiar'
                )}
              </Button>
            </div>
          </div>
        ) : null}

        {error ? (
          <p
            role="alert"
            className="mt-4 text-sm font-semibold text-danger-ink"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-6 flex justify-end gap-3">
          <Button
            ref={closeRef}
            variant="soft"
            onClick={onClose}
            disabled={isSharing}
          >
            Cerrar
          </Button>
          {shareUrl ? (
            <Button
              variant="danger"
              onClick={onRemove}
              disabled={isSharing}
              aria-busy={isSharing}
            >
              {isSharing ? (
                <Spinner className="size-4 animate-spin text-danger" />
              ) : null}
              Desactivar enlace
            </Button>
          ) : (
            !locked && (
              <Button
                onClick={onCreate}
                disabled={isSharing}
                aria-busy={isSharing}
              >
                {isSharing ? (
                  <Spinner className="size-4 animate-spin text-white" />
                ) : null}
                Crear enlace público
              </Button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
