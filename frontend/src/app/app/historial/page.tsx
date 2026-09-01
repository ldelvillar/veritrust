import type { Metadata } from 'next';

import { INITIAL_HISTORY_PATH } from '@/lib/historyQuery';
import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import HistorialClient from './HistorialClient';

export const metadata: Metadata = {
  title: 'Historial de Análisis',
  description:
    'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.',
};

export const dynamic = 'force-dynamic';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];

export default async function HistorialPage() {
  const initialData =
    await fetchJsonServer<HistoryPayload>(INITIAL_HISTORY_PATH);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <HistorialClient initialData={initialData} />
    </section>
  );
}
