import type { Metadata } from 'next';

import PageHeader from '@/components/PageHeader';
import UpgradePrompt from '@/components/UpgradePrompt';
import { fetchJsonServer, fetchPlanServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import DashboardClient from './DashboardClient';

export const metadata: Metadata = {
  title: 'Dashboard',
};

export const dynamic = 'force-dynamic';

type DashboardPayload =
  paths['/dashboard/summary']['get']['responses']['200']['content']['application/json'];

export default async function DashboardPage() {
  const plan = await fetchPlanServer();
  // Sin dashboard en el Plan no se llama a la API: el usuario ve la invitación, no un 403.
  const initialData = plan.limits.dashboard
    ? await fetchJsonServer<DashboardPayload>('/dashboard/summary')
    : null;

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 px-4 py-8 md:px-6 lg:py-10">
      {initialData ? (
        <DashboardClient initialData={initialData} />
      ) : (
        <>
          <PageHeader
            eyebrow="Panorama general"
            title="Dashboard"
            subtitle="Actividad, credibilidad y riesgos detectados en el conjunto de tus análisis."
          />
          <UpgradePrompt title="El dashboard es del plan Pro" className="py-12">
            Sigue tu volumen de análisis, la tasa de contenido fiable, las
            fuentes y dominios más frecuentes y las alertas de baja
            credibilidad.
          </UpgradePrompt>
        </>
      )}
    </section>
  );
}
