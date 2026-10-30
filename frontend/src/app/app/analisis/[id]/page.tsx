import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { ApiError } from '@/lib/apiClient';
import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import AnalisisClient, { HiddenAnalysis } from './AnalisisClient';

export const metadata: Metadata = {
  title: 'Resultado del análisis',
  description:
    'Resultado del análisis, incluyendo veredicto global, confianza y explicación médica.',
};

export const dynamic = 'force-dynamic';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface PageProps {
  params: Promise<{ id: string }>;
}

// null si no existe; 'hidden' si queda fuera de la ventana de History del Plan.
async function getAnalysis(
  id: string
): Promise<AnalysisDetail | 'hidden' | null> {
  try {
    return await fetchJsonServer<AnalysisDetail>(`/analysis/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.code === 'PLAN_REQUIRED')
      return 'hidden';
    if (err instanceof ApiError && (err.status === 404 || err.status === 400))
      return null;
    throw err;
  }
}

export default async function AnalisisPage({ params }: PageProps) {
  const { id } = await params;
  const initialData = await getAnalysis(id);
  if (!initialData) notFound();

  if (initialData === 'hidden') {
    return (
      <div className="flex flex-1 flex-col px-4 py-8 md:py-10">
        <HiddenAnalysis />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col px-4 py-8 md:py-10 print:p-[12mm]">
      <AnalisisClient id={id} initialData={initialData} />
    </div>
  );
}
