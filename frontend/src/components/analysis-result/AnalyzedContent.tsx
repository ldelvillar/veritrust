'use client';

import { useEffect, useId, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import Chevron from '@/assets/Chevron';
import DocumentIcon from '@/assets/Document';
import DownloadIcon from '@/assets/Download';
import GlobeIcon from '@/assets/Globe';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import PdfViewer from '@/components/PdfViewer';
import { fetchBlobWithAuth } from '@/lib/apiClient';
import { isPdfFilename } from './format';
import type { ReportView } from './types';

function AnalyzedPdf({
  analysisId,
  filename,
}: {
  analysisId: string;
  filename?: string | null;
}) {
  const { getToken } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    fetchBlobWithAuth(getToken, `/analysis/${analysisId}/file`)
      .then(blob => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setFailed(true);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [analysisId, getToken]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:hidden">
      <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <DocumentIcon className="size-4.5 text-primary" />
        Documento analizado
      </h3>
      <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
        {filename ?? 'PDF original que se verificó.'}
      </p>
      {failed ? (
        <p className="flex items-center gap-2 text-[13px] font-medium text-slate-400">
          <WarningIcon className="size-4 shrink-0 text-amber-500" />
          No se pudo cargar el PDF.
        </p>
      ) : url ? (
        <PdfViewer file={url} />
      ) : (
        <div className="flex min-h-40 items-center justify-center">
          <Spinner className="size-6 animate-spin text-primary" />
        </div>
      )}
    </div>
  );
}

function DownloadOriginalFile({
  analysisId,
  filename,
}: {
  analysisId: string;
  filename?: string | null;
}) {
  const { getToken } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [failed, setFailed] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    setFailed(false);
    try {
      const blob = await fetchBlobWithAuth(
        getToken,
        `/analysis/${analysisId}/file`
      );
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename || 'documento';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
    } catch {
      setFailed(true);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={downloading}
      className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
    >
      {downloading ? (
        <Spinner className="size-3.5 animate-spin" />
      ) : (
        <DownloadIcon className="size-3.5" />
      )}
      {failed ? 'Reintentar descarga' : 'Descargar original'}
    </button>
  );
}

export default function AnalyzedContent({
  result,
  isPublic,
}: {
  result: ReportView;
  isPublic: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  // Análisis por PDF: el binario requiere auth, así que en la vista pública
  // mostramos el texto extraído (cae a la rama de texto de abajo). Los archivos
  // .txt/.md también caen a la rama de texto: su contenido ya es el texto.
  const isPdf =
    result.source_type === 'file' && isPdfFilename(result.file_filename);
  if (isPdf && !isPublic && result.analysis_id) {
    return (
      <AnalyzedPdf
        analysisId={result.analysis_id}
        filename={result.file_filename}
      />
    );
  }

  // Análisis por URL: mostramos el enlace en lugar del texto completo.
  if (result.source_type === 'url') {
    if (!result.input_url) return null;
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:break-inside-avoid">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <GlobeIcon className="size-4.5 text-primary" />
          Contenido analizado
        </h3>
        <p className="mt-1 mb-3 text-[13px] leading-relaxed text-slate-500">
          Enlace de la noticia que se verificó.
        </p>
        <a
          href={result.input_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold break-all text-primary underline-offset-2 hover:underline focus:ring-2 focus:ring-primary/20 focus:outline-none"
        >
          {result.input_url}
        </a>
      </div>
    );
  }

  const text = result.input_text;
  if (!text) return null;

  // El binario requiere auth: solo se ofrece la descarga del original en la
  // vista propia de un análisis por archivo (.txt/.md; el PDF usa su visor).
  const originalFileId =
    result.source_type === 'file' && !isPublic ? result.analysis_id : undefined;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:break-inside-avoid">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <DocumentIcon className="size-4.5 text-primary" />
          Contenido analizado
        </h3>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          {originalFileId && (
            <DownloadOriginalFile
              analysisId={originalFileId}
              filename={result.file_filename}
            />
          )}
          <button
            type="button"
            onClick={() => setOpen(value => !value)}
            aria-expanded={open}
            aria-controls={panelId}
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none"
          >
            {open ? 'Ocultar' : 'Ver'} texto analizado
            <Chevron
              className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
              aria-hidden
            />
          </button>
        </div>
      </div>
      <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
        {originalFileId
          ? 'El texto extraído del archivo original que se verificó.'
          : 'El texto original tal y como se envió a verificar.'}
      </p>
      {/* Siempre en el DOM y colapsado con clases, para que el PDF (print:block)
          imprima el texto completo aunque esté oculto en pantalla. */}
      <div id={panelId} className={open ? 'block' : 'hidden print:block'}>
        <p className="mt-4 max-h-96 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-sm leading-relaxed whitespace-pre-wrap text-slate-700 print:max-h-none print:overflow-visible print:border-0 print:bg-transparent print:p-0">
          {text}
        </p>
      </div>
    </div>
  );
}
