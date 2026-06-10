import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import AnalysisResult from '@/components/AnalysisResult';
import { ApiError } from '@/lib/apiClient';
import { fetchPublicJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

export const metadata: Metadata = {
  title: 'Informe compartido | VeriTrust',
  description:
    'Informe de credibilidad compartido públicamente desde VeriTrust.',
  // No indexamos informes de usuarios en buscadores.
  robots: { index: false, follow: false },
};

export const dynamic = 'force-dynamic';

type PublicReport =
  paths['/shared/{token}']['get']['responses']['200']['content']['application/json'];

interface PageProps {
  params: Promise<{ token: string }>;
}

export default async function SharedReportPage({ params }: PageProps) {
  const { token } = await params;

  let data: PublicReport;
  try {
    data = await fetchPublicJsonServer<PublicReport>(`/shared/${token}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="flex flex-1 flex-col px-4 py-8 md:py-10">
      <div className="mx-auto mb-6 flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#e8e6f4] bg-white px-5 py-4 shadow-sm">
        <p className="text-sm font-semibold text-[#33344c]">
          Informe analizado con{' '}
          <span className="font-bold text-primary">VeriTrust</span> · detector de
          desinformación médica con IA
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white transition hover:bg-[#3722b8] focus:ring-4 focus:ring-primary/20 focus:outline-none"
        >
          Verifica tu propio contenido
        </Link>
      </div>
      <AnalysisResult result={data} isPublic />
    </div>
  );
}
