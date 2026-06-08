'use client';

import dynamic from 'next/dynamic';
import Spinner from '@/assets/Spinner';
import type { PdfDocumentProps } from './PdfDocument';

const PdfDocument = dynamic(() => import('./PdfDocument'), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-60 items-center justify-center rounded-xl border border-slate-200 bg-slate-50">
      <Spinner className="size-6 animate-spin text-primary" />
    </div>
  ),
});

export default function PdfViewer(props: PdfDocumentProps) {
  return <PdfDocument {...props} />;
}
