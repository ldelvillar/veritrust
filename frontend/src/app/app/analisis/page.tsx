import type { Metadata } from 'next';

import AnalysisForm from '@/components/AnalysisForm';

export const metadata: Metadata = {
  title: 'Analizar | VeriTrust',
};

export default function AnalisisPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <section className="mt-12 w-full max-w-4xl px-4 text-center md:mt-16 md:px-6">
        <h1 className="text-3xl leading-tight font-bold text-gray-900 sm:text-4xl md:text-5xl">
          Detector de Desinformación Médica
        </h1>
        <p className="mt-3 text-base leading-relaxed text-gray-600 sm:mt-4 sm:text-lg">
          Esta herramienta utiliza un sistema multiagente que busca entre bases
          de datos especializadas y analiza patrones lingüísticos para detectar
          afirmaciones médicas falsas.
        </p>
      </section>

      <AnalysisForm />
    </div>
  );
}
