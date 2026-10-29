import { unstable_rethrow } from 'next/navigation';

import Sidebar from '@/components/layout/Sidebar';
import PlanProvider from '@/components/PlanProvider';
import type { PlanResponse } from '@/lib/plan';
import { fetchPlanServer } from '@/lib/serverApi';

// Sin Plan precargado la app sigue en pie: el cliente lo pide y la API aplica sus límites.
async function loadPlan(): Promise<PlanResponse | null> {
  try {
    return await fetchPlanServer();
  } catch (err) {
    // Los errores de control de Next (renderizado dinámico, redirecciones) no son fallos de la API.
    unstable_rethrow(err);
    return null;
  }
}

export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const initialPlan = await loadPlan();

  return (
    <PlanProvider initialPlan={initialPlan}>
      <div className="flex min-h-screen flex-col bg-white md:flex-row">
        <Sidebar />
        <main className="flex min-w-0 flex-1 flex-col bg-[linear-gradient(180deg,var(--color-surface-subtle),var(--color-surface)_360px)] print:bg-white print:bg-none">
          {children}
        </main>
      </div>
    </PlanProvider>
  );
}
