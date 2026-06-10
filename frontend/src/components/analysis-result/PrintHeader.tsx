// Cabecera con marca que solo aparece al imprimir (PDF), no en pantalla.
export default function PrintHeader({ createdAt }: { createdAt: string }) {
  const formattedDate = new Date(createdAt).toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="hidden items-center justify-between border-b border-slate-200 pb-4 print:flex">
      <div className="flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element -- the SVG Logo embeds a pattern image that Chromium prints blank; a raster <img> prints reliably */}
        <img
          src="/images/logo-1316x1316-no-bg.png"
          alt="VeriTrust"
          width={24}
          height={24}
          className="h-6 w-6"
        />
        <span className="text-lg font-bold tracking-tight text-slate-900">
          VeriTrust
        </span>
      </div>
      <span className="text-xs font-semibold text-slate-500">
        Informe de credibilidad · {formattedDate}
      </span>
    </div>
  );
}
