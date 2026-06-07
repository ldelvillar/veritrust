import type { Metadata } from 'next';

import AnalysisForm from './_components/AnalysisForm';

export const metadata: Metadata = {
  title: 'Analizar | VeriTrust',
};

export default function AnalisisPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <h1 className="mt-12 text-3xl leading-tight font-bold text-gray-900 sm:text-4xl md:text-5xl">
        Detector de Desinformación Médica
      </h1>

      <AnalysisForm />
    </div>
  );
}
