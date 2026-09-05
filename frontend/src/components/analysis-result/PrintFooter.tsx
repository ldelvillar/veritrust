/* Pie con marca que solo aparece al imprimir (PDF), no en pantalla. */
import { SITE_CONFIG } from '@/config/site';

export default function PrintFooter() {
  return (
    <div className="hidden border-t border-line pt-4 text-2xs leading-relaxed text-faint print:block">
      Informe generado por VeriTrust ·{' '}
      <a
        href={SITE_CONFIG.domain}
        className="font-semibold text-muted underline-offset-2 hover:underline"
      >
        {SITE_CONFIG.domain}
      </a>
      . Herramienta orientativa de credibilidad: no emite diagnósticos ni
      sustituye el consejo de un profesional sanitario.
    </div>
  );
}
