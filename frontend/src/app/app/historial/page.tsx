import type { Metadata } from 'next';

import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import HistorialClient from './HistorialClient';

export const metadata: Metadata = {
  title: 'Historial de Análisis | VeriTrust',
  description:
    'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.',
};

export const dynamic = 'force-dynamic';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];

const PAGE_SIZE = 10;
const INITIAL_PATH = `/history?page=1&page_size=${PAGE_SIZE}&source_type=all&date_range=all&date_sort=desc`;

export default async function HistorialPage() {
  const initialData = await fetchJsonServer<HistoryPayload>(INITIAL_PATH);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <HistorialClient initialData={initialData} />
    </section>
  );
}
