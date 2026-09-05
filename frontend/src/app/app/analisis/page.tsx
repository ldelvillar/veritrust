import type { Metadata } from 'next';

import { fetchPublicJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

import AnalysisForm from './_components/AnalysisForm';

export const metadata: Metadata = {
  title: 'Nuevo Análisis',
};

export const dynamic = 'force-dynamic';

type ClientConfig =
  paths['/config']['get']['responses']['200']['content']['application/json'];

// Si la API no responde, el formulario no inventa límites: delega la validación en el servidor.
async function loadLimits(): Promise<ClientConfig | null> {
  try {
    return await fetchPublicJsonServer<ClientConfig>('/config');
  } catch {
    return null;
  }
}

export default async function AnalisisPage() {
  const limits = await loadLimits();

  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-11 sm:py-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(var(--color-line-strong)_1.1px,transparent_1.1px)] mask-[radial-gradient(circle_at_50%_42%,#000_50%,transparent_82%)] bg-size-[22px_22px] opacity-60 [-webkit-mask-image:radial-gradient(circle_at_50%_42%,#000_50%,transparent_82%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(580px_360px_at_50%_40%,rgba(12,79,82,.15),transparent_70%)]"
      />

      <div className="relative mb-5.5 max-w-150 text-center">
        <h1 className="font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md">
          Antes de compartirlo,
          <br />
          <em className="italic">compruébalo</em>.
        </h1>
      </div>

      <AnalysisForm limits={limits} />
    </div>
  );
}
