import Magnifier from '@/assets/Magnifier';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';

const FAILURE_MESSAGES: Record<string, string> = {
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
  // No es un fallo del sistema: el contenido no traía afirmaciones médicas que verificar
  if (errorCode === 'NO_MEDICAL_CLAIMS') {
    return (
      <div className="flex w-full flex-col items-center gap-4 rounded-xl border border-line bg-white p-10 text-center shadow-sm">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-[#eeebfc] text-primary">
          <Magnifier className="size-7" />
        </div>
        <h3 className="text-xl font-bold text-ink">
          No encontramos afirmaciones médicas que verificar
        </h3>
        <p className="max-w-md text-sm leading-relaxed text-muted">
          Revisamos el contenido, pero no contenía afirmaciones médicas
          concretas que se puedan contrastar con literatura biomédica. Prueba
          con un texto que afirme algo sobre un tratamiento, síntoma, alimento o
          medida de prevención.
        </p>
        <Button href="/app/analisis" className="mt-2">
          Analizar otro contenido
        </Button>
      </div>
    );
  }

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
          <Button
            onClick={onRetry}
            disabled={isRetrying}
            aria-busy={isRetrying}
          >
            {isRetrying && <Spinner className="size-4 animate-spin" />}
            {isRetrying ? 'Reintentando…' : 'Reintentar análisis'}
          </Button>
        )}
        <Button href="/app/analisis" variant={onRetry ? 'soft' : 'primary'}>
          Analizar otro contenido
        </Button>
      </div>
      {retryError && (
        <p role="alert" className="text-xs font-semibold text-red-600">
          {retryError}
        </p>
      )}
    </div>
  );
}
