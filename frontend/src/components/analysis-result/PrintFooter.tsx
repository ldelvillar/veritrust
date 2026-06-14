// Pie con marca que solo aparece al imprimir (PDF), no en pantalla.
export default function PrintFooter() {
  return (
    <div className="hidden border-t border-line pt-4 text-[11px] leading-relaxed text-faint print:block">
      Informe generado por VeriTrust ·{' '}
      <a
        href="https://tfg-hazel.vercel.app"
        className="font-semibold text-muted underline-offset-2 hover:underline"
      >
        tfg-hazel.vercel.app
      </a>
      . Herramienta orientativa de credibilidad: no emite diagnósticos ni
      sustituye el consejo de un profesional sanitario.
    </div>
  );
}
