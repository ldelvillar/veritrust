import type { Metadata } from 'next';

import DocumentIcon from '@/assets/Document';
import AnalysisResult from '@/components/AnalysisResult';
import PublicButton from '@/components/PublicButton';
import type { ReportView } from '@/components/analysis-result/types';

export const metadata: Metadata = {
  title: 'Informe de ejemplo',
  description:
    'Análisis real de VeriTrust sobre un texto de prueba, para ver cómo se presenta un informe de credibilidad.',
};

// Real Analysis from 14 Oct 2026, copied as is from the API to show the format without waiting for the pipeline.
const SAMPLE_REPORT: ReportView = {
  source_type: 'text',
  input_text:
    'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común y refuerza el sistema inmunitario sin ningún riesgo, según un estudio reciente.',
  input_url: null,
  label: 'falsa',
  confidence: 0.7083333333333333,
  evidence_coverage: 1.0,
  explanation: `**VEREDICTO GLOBAL: FALSO**
El contenido analizado contiene afirmaciones **falsas** según la evidencia científica disponible, con un nivel de seguridad del 70.83%.

---

### **Análisis detallado de las afirmaciones**

#### **1. Afirmación: "El consumo diario de vitamina C en dosis altas previene por completo el resfriado común."**
**Veredicto:** **Falsa**
**Fundamentación:**
- La fuente *The Long History of Vitamin C: From Prevention of the Common Cold to Potential Aid in the Treatment of COVID-19* (Frontiers in Immunology, 2020) **contradice** esta afirmación. Según su resumen:
  > *"No current clinical recommendations support the possibility of significantly decreasing the risk of respiratory infections by using high-dose supplements of vitamin C in a well-nourished general population."*
  Además, se señala que, aunque una dieta equilibrada que incluya vitamina C **reduce la susceptibilidad a infecciones**, **no hay evidencia** de que los suplementos en dosis altas prevengan el resfriado común en la población general.
- La fuente *Vitamin C in the Prevention and Treatment of the Common Cold* (American Journal of Lifestyle Medicine, 2016) **no es concluyente** sobre esta afirmación, pero su resumen indica que:
  > *"The purpose of this article is to review the current data on the relationship between vitamin C and immune function, specifically, the utility of vitamin C supplementation in the prevention and treatment of the common cold."*
  Esto implica que **no existe consenso** sobre su eficacia preventiva, y menos aún sobre una prevención "por completo".

**Conclusión:** No hay evidencia que respalde que la vitamina C en dosis altas prevenga el resfriado común de manera absoluta.

---

#### **2. Afirmación: "El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo."**
**Veredicto:** **Falsa**
**Fundamentación:**
- La fuente *Vitamin C-Beyond Deficiency: Mechanisms, Clinical Applications, Formulation and Dosing Considerations, and Safety Across Stress-Responsive Conditions* (2026) **contradice** esta afirmación. Según su resumen:
  > *"The strength of evidence differs substantially across domains: biochemical functions and deficiency correction are well established, whereas benefits of supraphysiologic oral supplementation in vitamin C-replete patients remain uncertain."*
  Además, se advierte que:
  > *"Because evidence for high-dose oral supplementation remains limited and condition-specific, such use should be individualized, time-limited, and clinician-monitored rather than presented as a population-level recommendation or evidence-defined therapeutic target."*
  Esto significa que **no hay pruebas sólidas** de que la vitamina C en dosis altas refuerce el sistema inmunitario en personas con niveles normales de vitamina C, y su uso debe ser supervisado médicamente.
- La fuente *High-Dose Intravenous Vitamin C in Critical Illness: A Translational Exposure-Response Framework for Biomarker-Guided Precision Therapy* (2026) también **contradice** la idea de que no hay riesgos. Según su resumen:
  > *"Intravenous administration enables plasma concentrations in the millimolar range (≈1-5 mM), far exceeding those achievable with oral dosing (<100 µM), thereby reaching thresholds required for pharmacodynamic effects on oxidative stress, immune signaling, and endothelial function."*
  Esto indica que **las dosis altas (especialmente por vía intravenosa) pueden tener efectos farmacológicos**, pero su seguridad y eficacia dependen de múltiples factores (timing, paciente, etc.), y **no están exentas de riesgos**.

**Conclusión:** No existe evidencia de que la vitamina C en dosis altas refuerce el sistema inmunitario sin riesgos, y su uso en exceso puede no ser seguro.

---
### **Resumen final**
- **Ninguna de las dos afirmaciones tiene respaldo científico.**
- La vitamina C es un nutriente esencial, pero **su suplementación en dosis altas no previene el resfriado común ni refuerza el sistema inmunitario de manera universal o sin riesgos**, según las fuentes consultadas.
- Las recomendaciones actuales **no avalan** el uso de suplementos de vitamina C en dosis altas para estos fines en la población general.`,
  status: 'done',
  error_code: null,
  created_at: '2026-10-14T10:40:29.641Z',
  completed_at: '2026-10-14T10:40:49.214Z',
  file_filename: null,
  claims: [
    {
      text: 'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
      label: 'falsa',
      confidence: 0.6666666666666666,
      verdict: 'fake',
    },
    {
      text: 'El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo.',
      label: 'falsa',
      confidence: 0.75,
      verdict: 'fake',
    },
  ],
  sources: [
    {
      title:
        'The Long History of Vitamin C: From Prevention of the Common Cold to Potential Aid in the Treatment of COVID-19.',
      url: 'https://doi.org/10.3389/fimmu.2020.574029',
      source: 'Frontiers in immunology',
      year: '2020',
      statements: [
        {
          claim_index: 0,
          text: 'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
          stance: 'contradicts',
        },
      ],
    },
    {
      title: 'Vitamin C in the Prevention and Treatment of the Common Cold.',
      url: 'https://doi.org/10.1177/1559827616629092',
      source: 'American journal of lifestyle medicine',
      year: '2016',
      statements: [
        {
          claim_index: 0,
          text: 'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
          stance: 'inconclusive',
        },
      ],
    },
    {
      title:
        'Vitamin C-Beyond Deficiency: Mechanisms, Clinical Applications, Formulation and Dosing Considerations, and Safety Across Stress-Responsive Conditions.',
      url: 'https://doi.org/10.3390/nu18142319',
      source: null,
      year: '2026',
      statements: [
        {
          claim_index: 1,
          text: 'El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo.',
          stance: 'contradicts',
        },
      ],
    },
    {
      title:
        'High-Dose Intravenous Vitamin C in Critical Illness: A Translational Exposure-Response Framework for Biomarker-Guided Precision Therapy.',
      url: 'https://doi.org/10.3390/medsci14030400',
      source: null,
      year: '2026',
      statements: [
        {
          claim_index: 1,
          text: 'El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo.',
          stance: 'contradicts',
        },
      ],
    },
  ],
  share_token: null,
  stage: 'health_expert',
  verdict: 'fake',
  credibility: 29,
  confidence_level: 'medium',
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
          Este es un <b className="font-bold text-ink">análisis real</b> de
          VeriTrust sobre un texto de prueba, hecho el 14 de octubre de 2026.
        </p>
        <PublicButton href="/app/analisis" className="shrink-0">
          Analizar mi contenido
        </PublicButton>
      </div>

      <AnalysisResult result={SAMPLE_REPORT} isPublic={true} />
    </section>
  );
}
