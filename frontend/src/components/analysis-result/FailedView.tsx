import Link from 'next/link';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';

const FAILURE_MESSAGES: Record<string, string> = {
  NO_MEDICAL_CLAIMS:
    'No se detectaron afirmaciones médicas verificables en el contenido proporcionado.',
  URL_EXTRACTION:
    'No se pudo extraer el contenido de la URL. Comprueba que el enlace sea válido y accesible.',
  CONNECTION:
    'No se pudo conectar con el motor de análisis. Inténtalo de nuevo en unos minutos.',
  SERVICE_UNAVAILABLE:
    'El servicio de análisis no estaba disponible y no se pudo procesar la noticia. Inténtalo de nuevo.',
  INTERNAL:
    'Ocurrió un error inesperado al procesar el análisis. Inténtalo de nuevo.',
  FILE_EXTRACTION:
    'No se pudo extraer texto del archivo. Puede estar protegido, dañado, vacío o ser un documento escaneado sin texto seleccionable.',
};

export default function FailedView({
  errorCode,
  onRetry,
  isRetrying,
  retryError,
}: {
  errorCode: string | null | undefined;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
}) {
  const message =
    (errorCode && FAILURE_MESSAGES[errorCode]) ?? FAILURE_MESSAGES.INTERNAL;

  return (
    <div className="flex w-full flex-col items-center gap-4 rounded-xl border border-red-100 bg-red-50 p-10 text-center shadow-sm">
      <WarningIcon className="size-10 text-red-500" />
      <h3 className="text-xl font-bold text-red-700">
        No se pudo completar el análisis
      </h3>
      <p className="max-w-md text-sm leading-relaxed text-red-600">{message}</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            aria-busy={isRetrying}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-4 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRetrying && <Spinner className="size-4 animate-spin" />}
            {isRetrying ? 'Reintentando…' : 'Reintentar análisis'}
          </button>
        )}
        <Link
          href="/app/analisis"
          className={
            onRetry
              ? 'inline-flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-600 transition hover:bg-red-100 focus:ring-4 focus:ring-red-200 focus:outline-none'
              : 'inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-4 focus:ring-primary/20 focus:outline-none'
          }
        >
          Analizar otro contenido
        </Link>
      </div>
      {retryError && (
        <p role="alert" className="text-xs font-semibold text-red-600">
          {retryError}
        </p>
      )}
    </div>
  );
}
