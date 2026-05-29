'use client';

import Result from '@/components/Result';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { paths } from '@/types/api';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface AnalisisClientProps {
  id: string;
  initialData: AnalysisDetail;
}

export default function AnalisisClient({
  id,
  initialData,
}: AnalisisClientProps) {
  const { data } = useApiQuery<AnalysisDetail>(`/analysis/${id}`, {
    fallbackData: initialData,
    // El worker procesa el análisis en segundo plano: hacemos polling cada 2s
    // mientras siga 'pending' y paramos en cuanto termina ('done' o 'failed').
    refreshInterval: latest => (latest?.status === 'pending' ? 2000 : 0),
  });
  return <Result result={data ?? initialData} />;
}
