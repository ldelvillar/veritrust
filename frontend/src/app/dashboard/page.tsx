import type { Metadata } from 'next';

import { fetchJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import DashboardClient from './DashboardClient';

export const metadata: Metadata = {
  title: 'Dashboard | VeriTrust',
};

export const dynamic = 'force-dynamic';

type DashboardPayload =
  paths['/dashboard/summary']['get']['responses']['200']['content']['application/json'];

export default async function DashboardPage() {
  const initialData =
    await fetchJsonServer<DashboardPayload>('/dashboard/summary');

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 px-4 py-8 md:px-6 lg:py-10">
      <DashboardClient initialData={initialData} />
    </section>
  );
}
