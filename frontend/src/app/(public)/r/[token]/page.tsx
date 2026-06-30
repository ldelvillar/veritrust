import type { Metadata } from 'next';
import { cache } from 'react';
import { notFound } from 'next/navigation';

import AnalysisResult from '@/components/AnalysisResult';
import Button from '@/components/Button';
import { getVerdictInfo } from '@/components/analysis-result/format';
import { ApiError } from '@/lib/apiClient';
import { fetchPublicJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

export const dynamic = 'force-dynamic';

type PublicReport =
  paths['/shared/{token}']['get']['responses']['200']['content']['application/json'];

interface PageProps {
  params: Promise<{ token: string }>;
}

// Los informes de usuarios nunca se indexan
const NO_INDEX = { index: false, follow: false } as const;

// cache() deduplica la petición entre generateMetadata y la página en un render.
const getReport = cache(async (token: string): Promise<PublicReport | null> => {
  try {
    return await fetchPublicJsonServer<PublicReport>(`/shared/${token}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
});

// Recorta el texto a una línea legible para la descripción de la previsualización.
function truncate(text: string, max: number): string {
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

// Asunto analizado (dominio, archivo o fragmento del texto) para dar contexto.
function analyzedSubject(report: PublicReport): string | null {
  if (report.source_type === 'url' && report.input_url) {
    try {
      return new URL(report.input_url).hostname.replace(/^www\./, '');
    } catch {
      return report.input_url;
    }
  }
  if (report.source_type === 'file' && report.file_filename) {
    return report.file_filename;
  }
  if (report.input_text) return truncate(report.input_text, 100);
  return null;
}

function buildDescription(report: PublicReport, verdictText: string): string {
  const subject = analyzedSubject(report);
  const lead = subject ? `«${subject}» — ${verdictText}.` : `${verdictText}.`;
  return `${lead} Análisis de credibilidad médica verificado afirmación por afirmación con VeriTrust.`;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { token } = await params;

  let report: PublicReport | null;
  try {
    report = await getReport(token);
  } catch {
    // Si el backend falla al pintar metadatos, no rompemos el <head> de la página.
    report = null;
  }

  if (!report) {
    return {
      title: 'Informe Compartido',
      description:
        'Informe de credibilidad compartido públicamente desde VeriTrust.',
      robots: NO_INDEX,
    };
  }

  const verdict = getVerdictInfo(report.verdict);
  const score = report.credibility;
  const headline =
    score != null ? `${verdict.text} · ${score}/100` : verdict.text;
  const description = buildDescription(report, verdict.text);

  return {
    title: headline,
    description,
    robots: NO_INDEX,
    openGraph: {
      title: headline,
      description,
      siteName: 'VeriTrust',
      type: 'article',
      locale: 'es_ES',
    },
    twitter: {
      card: 'summary_large_image',
      title: headline,
      description,
    },
  };
}

export default async function SharedReportPage({ params }: PageProps) {
  const { token } = await params;

  const data = await getReport(token);
  if (!data) notFound();

  return (
    <div className="flex flex-1 flex-col px-4 py-8 md:py-10">
      <div className="mx-auto mb-6 flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-white px-5 py-4 shadow-sm">
        <p className="text-sm font-semibold text-body">
          Informe analizado con{' '}
          <span className="font-bold text-primary">VeriTrust</span> · detector
          de desinformación médica con IA
        </p>
        <Button href="/">Verifica tu propio contenido</Button>
      </div>
      <AnalysisResult result={data} isPublic />
    </div>
  );
}
