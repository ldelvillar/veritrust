import type { Metadata } from 'next';

import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import AnalisisClient from './AnalisisClient';

export const metadata: Metadata = {
  title: 'Resultado del análisis | VeriTrust',
  description:
    'Resultado del análisis, incluyendo veredicto global, confianza y explicación médica.',
};

export const dynamic = 'force-dynamic';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function AnalisisPage({ params }: PageProps) {
  const { id } = await params;
  const initialData = await fetchJsonServer<AnalysisDetail>(`/analysis/${id}`);

  return (
    <div className="flex flex-1 flex-col px-4 py-8 md:py-10 print:p-[12mm]">
      <AnalisisClient id={id} initialData={initialData} />
    </div>
  );
}
