import { unstable_rethrow } from 'next/navigation';

import Sidebar from '@/components/layout/Sidebar';
import PlanProvider from '@/components/PlanProvider';
import type { PlanResponse } from '@/lib/plan';
import { fetchPlanServer } from '@/lib/serverApi';

// Without a preloaded Plan the app still works, as the client requests it and the API enforces its limits.
async function loadPlan(): Promise<PlanResponse | null> {
  try {
    return await fetchPlanServer();
  } catch (err) {
    // Next's control errors (dynamic rendering, redirects) are not API failures.
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
