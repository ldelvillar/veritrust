import type { Metadata } from 'next';

import DocumentIcon from '@/assets/Document';
import AnalysisResult from '@/components/AnalysisResult';
import Button from '@/components/Button';
import type { ReportView } from '@/components/analysis-result/types';

export const metadata: Metadata = {
  title: 'Informe de ejemplo',
  description:
    'Informe de credibilidad de ejemplo con datos de muestra para ver cómo VeriTrust presenta un análisis.',
};

// Informe ficticio con datos de muestra para enseñar el formato sin esperar al pipeline.
const SAMPLE_REPORT: ReportView = {
  source_type: 'text',
  input_text:
    'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común y refuerza el sistema inmunitario sin ningún riesgo, según un estudio reciente.',
  input_url: null,
  label: 'falsa',
  confidence: 0.84,
  explanation: `El texto **mezcla una afirmación cierta con conclusiones que la evidencia no respalda**, por lo que su credibilidad global es baja.

Es correcto que la vitamina C contribuye al funcionamiento normal del sistema inmunitario. Sin embargo, la idea de que su consumo diario **previene por completo** el resfriado común no se sostiene: las revisiones sistemáticas no encuentran una reducción de la incidencia en la población general. Además, presentar las dosis altas como algo "sin ningún riesgo" es engañoso, ya que pueden causar molestias gastrointestinales y no están exentas de efectos.

Ante afirmaciones de salud absolutas ("previene por completo", "sin ningún riesgo"), conviene contrastar siempre con fuentes médicas reconocidas.`,
  status: 'done',
  error_code: null,
  created_at: '2026-06-13T10:52:00.000Z',
  completed_at: '2026-06-13T10:55:00.000Z',
  file_filename: null,
  claims: [
    {
      text: 'La vitamina C es esencial para el funcionamiento del sistema inmunitario.',
      label: 'verdadera',
      confidence: 0.94,
      verdict: 'real',
    },
    {
      text: 'El consumo diario de vitamina C previene por completo el resfriado común.',
      label: 'falsa',
      confidence: 0.9,
      verdict: 'fake',
    },
    {
      text: 'Las dosis altas de vitamina C no presentan ningún riesgo.',
      label: 'incierta',
      confidence: 0.52,
      verdict: 'uncertain',
    },
  ],
  sources: [
    {
      title: 'Vitamin C for preventing and treating the common cold',
      url: 'https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD000980.pub4/full',
      source: 'Cochrane',
      year: '2013',
      statements: [
        {
          text: 'El consumo diario de vitamina C previene por completo el resfriado común.',
          stance: 'contradicts',
        },
      ],
    },
    {
      title: 'Vitamin C and Immune Function',
      url: 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5707683/',
      source: 'Nutrients',
      year: '2017',
      statements: [
        {
          text: 'La vitamina C es esencial para el funcionamiento del sistema inmunitario.',
          stance: 'supports',
        },
      ],
    },
    {
      title: 'Vitamin C — Health Professional Fact Sheet',
      url: 'https://ods.od.nih.gov/factsheets/VitaminC-HealthProfessional/',
      source: 'NIH',
      year: '2021',
      statements: [
        {
          text: 'Las dosis altas de vitamina C no presentan ningún riesgo.',
          stance: 'inconclusive',
        },
      ],
    },
  ],
  share_token: null,
  stage: null,
  verdict: 'fake',
  credibility: 16,
};

export default function EjemploPage() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-primary/15 bg-primary/8 px-5 py-4">
        <p className="flex items-center gap-2.5 text-sm font-semibold text-body">
          <DocumentIcon
            className="size-4.5 shrink-0 text-primary"
            aria-hidden
          />
          Este es un <b className="font-bold text-ink">informe de ejemplo</b>{' '}
          con datos de muestra para que veas cómo se presenta un análisis.
        </p>
        <Button href="/app/analisis" className="shrink-0">
          Analizar mi contenido
        </Button>
      </div>

      <AnalysisResult result={SAMPLE_REPORT} isPublic={true} />
    </section>
  );
}
