import type { Metadata } from 'next';

import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import CuentaClient from './CuentaClient';

export const metadata: Metadata = {
  title: 'Cuenta y datos',
  description:
    'Consulta tu cuenta de VeriTrust, exporta tu historial de análisis y gestiona tus datos personales.',
};

export const dynamic = 'force-dynamic';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];

const COUNT_PATH =
  '/history?page=1&page_size=1&source_type=all&verdict=all&status=all&date_range=all&date_sort=desc';

export default async function CuentaPage() {
  const data = await fetchJsonServer<HistoryPayload>(COUNT_PATH);
  const initialCount = typeof data?.count === 'number' ? data.count : 0;

  return (
    <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <CuentaClient initialCount={initialCount} />
    </section>
  );
}
