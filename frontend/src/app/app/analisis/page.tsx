import type { Metadata } from 'next';

import AnalysisForm from './_components/AnalysisForm';

export const metadata: Metadata = {
  title: 'Nuevo Análisis',
};

export default function AnalisisPage() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-6 py-11 sm:py-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(#dcd9ee_1.1px,transparent_1.1px)] mask-[radial-gradient(circle_at_50%_42%,#000_50%,transparent_82%)] bg-size-[22px_22px] opacity-60 [-webkit-mask-image:radial-gradient(circle_at_50%_42%,#000_50%,transparent_82%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(580px_360px_at_50%_40%,rgba(90,68,232,.15),transparent_70%)]"
      />

      <div className="relative mb-5.5 max-w-150 text-center">
        <p className="mb-2.5 text-xs font-extrabold tracking-[0.13em] text-primary uppercase">
          Verificación de afirmaciones médicas
        </p>
        <h1 className="text-[25px] leading-[1.1] font-extrabold tracking-[-0.03em] text-ink md:text-[30px]">
          Comprueba una afirmación de salud
        </h1>
        <p className="mt-2.25 text-[15px] leading-normal font-medium text-muted">
          Pega un texto, un enlace o sube un documento. Lo contrastamos con la
          literatura médica.
        </p>
      </div>

      <AnalysisForm />
    </div>
  );
}
