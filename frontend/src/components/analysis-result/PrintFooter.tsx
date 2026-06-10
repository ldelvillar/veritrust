// Pie con marca que solo aparece al imprimir (PDF), no en pantalla.
export default function PrintFooter() {
  return (
    <div className="hidden border-t border-slate-200 pt-4 text-[11px] leading-relaxed text-slate-400 print:block">
      Informe generado por VeriTrust ·{' '}
      <a
        href="https://tfg-hazel.vercel.app"
        className="font-semibold text-slate-500 underline-offset-2 hover:underline"
      >
        tfg-hazel.vercel.app
      </a>
      . Herramienta orientativa de credibilidad: no emite diagnósticos ni
      sustituye el consejo de un profesional sanitario.
    </div>
  );
}
