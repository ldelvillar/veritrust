'use client';

import { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import Chevron from '@/assets/Chevron';

// El worker de pdf.js se carga desde un CDN con la versión exacta que usa
// react-pdf, evitando configurar el empaquetado del worker en Turbopack.
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export interface PdfDocumentProps {
  /** Origen del PDF: una URL (string) o un File/Blob local. */
  file: string | Blob;
  className?: string;
}

const MAX_PAGE_WIDTH = 820;

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-60 items-center justify-center p-6 text-center text-sm font-medium text-slate-500">
      {children}
    </div>
  );
}

export default function PdfDocument({ file, className }: PdfDocumentProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState<number>();
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const measure = () => setWidth(containerRef.current?.clientWidth);
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  // Reinicia el estado al cambiar de documento (patrón de estado derivado).
  const [prevFile, setPrevFile] = useState(file);
  if (file !== prevFile) {
    setPrevFile(file);
    setPage(1);
    setNumPages(0);
    setFailed(false);
  }

  const pageWidth = width ? Math.min(width - 2, MAX_PAGE_WIDTH) : undefined;

  return (
    <div
      ref={containerRef}
      className={`overflow-hidden rounded-xl border border-slate-200 bg-slate-50 ${className ?? ''}`}
    >
      {failed ? (
        <CenteredMessage>
          <span className="flex flex-col items-center gap-2 text-slate-500">
            <WarningIcon className="size-6 text-amber-500" />
            No se pudo mostrar el PDF.
          </span>
        </CenteredMessage>
      ) : (
        <>
          <div className="flex max-h-160 justify-center overflow-auto p-3">
            <Document
              file={file}
              onLoadSuccess={({ numPages: total }) => setNumPages(total)}
              onLoadError={() => setFailed(true)}
              loading={
                <CenteredMessage>
                  <Spinner className="size-6 animate-spin text-primary" />
                </CenteredMessage>
              }
              error={
                <CenteredMessage>No se pudo cargar el PDF.</CenteredMessage>
              }
            >
              <Page
                pageNumber={page}
                width={pageWidth}
                renderAnnotationLayer={false}
                loading={
                  <CenteredMessage>
                    <Spinner className="size-6 animate-spin text-primary" />
                  </CenteredMessage>
                }
                className="shadow-sm"
              />
            </Document>
          </div>

          {numPages > 1 && (
            <div className="flex items-center justify-center gap-4 border-t border-slate-200 bg-white px-4 py-2.5">
              <button
                type="button"
                onClick={() => setPage(value => Math.max(1, value - 1))}
                disabled={page <= 1}
                aria-label="Página anterior"
                className="grid size-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Chevron className="size-4 rotate-90" />
              </button>
              <span className="text-sm font-semibold text-slate-600 tabular-nums">
                Página {page} de {numPages}
              </span>
              <button
                type="button"
                onClick={() => setPage(value => Math.min(numPages, value + 1))}
                disabled={page >= numPages}
                aria-label="Página siguiente"
                className="grid size-8 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Chevron className="size-4 -rotate-90" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
