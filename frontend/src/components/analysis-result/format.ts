import Check from '@/assets/Check';
import Cross from '@/assets/Cross';
import WarningIcon from '@/assets/Warning';
import type { Verdict } from './types';

// Fuente única de veredicto: etiqueta y clases de color respaldadas por tokens semánticos.
export const VERDICT_META: Record<
  Verdict,
  { label: string; solid: string; soft: string; ink: string; pill: string }
> = {
  real: {
    label: 'Verdadero',
    solid: 'bg-verdict-real',
    soft: 'bg-verdict-real-soft',
    ink: 'text-verdict-real-ink',
    pill: 'bg-verdict-real-soft text-verdict-real-ink',
  },
  fake: {
    label: 'Falso',
    solid: 'bg-verdict-fake',
    soft: 'bg-verdict-fake-soft',
    ink: 'text-verdict-fake-ink',
    pill: 'bg-verdict-fake-soft text-verdict-fake-ink',
  },
  uncertain: {
    label: 'Dudoso',
    solid: 'bg-verdict-uncertain',
    soft: 'bg-verdict-uncertain-soft',
    ink: 'text-verdict-uncertain-ink',
    pill: 'bg-verdict-uncertain-soft text-verdict-uncertain-ink',
  },
};

// Vocabulario único de veredicto para todo el producto
export const VERDICT_LABEL: Record<Verdict, string> = {
  real: VERDICT_META.real.label,
  fake: VERDICT_META.fake.label,
  uncertain: VERDICT_META.uncertain.label,
};

export function getVerdictInfo(verdict: Verdict): {
  text: string;
  description: string;
  band: string;
} {
  if (verdict === 'real') {
    return {
      text: `Contenido ${VERDICT_LABEL.real.toLowerCase()}`,
      description:
        'El contenido muestra alta consistencia factual con fuentes médicas reputadas y bajos indicadores de información errónea.',
      band: 'linear-gradient(135deg,#2bc488,#10a566 70%,#0c9059)',
    };
  }
  if (verdict === 'fake') {
    return {
      text: `Contenido ${VERDICT_LABEL.fake.toLowerCase()}`,
      description:
        'El contenido contiene afirmaciones que contradicen o no pueden ser verificadas con fuentes médicas reconocidas.',
      band: 'linear-gradient(135deg,#e2607a,#d23c5d 70%,#c33051)',
    };
  }
  return {
    text: `Contenido ${VERDICT_LABEL.uncertain.toLowerCase()}`,
    description:
      'No se ha podido determinar con certeza la veracidad del contenido. Se recomienda consultar fuentes adicionales.',
    band: 'linear-gradient(135deg,#e8b057,#d98e29 70%,#c97e1c)',
  };
}

export function normalizeFraction(value: number): number {
  return value <= 1 ? value : value / 100;
}

export function formatCoverage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function confidenceLabel(
  confidence: number | null | undefined
): string | null {
  if (confidence == null) return null;
  const fraction = normalizeFraction(confidence);
  if (fraction >= 0.85) return 'Confianza alta';
  if (fraction >= 0.6) return 'Confianza media';
  return 'Confianza baja';
}

export function getClaimStyle(verdict: Verdict): {
  Icon: typeof Check;
  text: string;
  tile: string;
  pill: string;
} {
  if (verdict === 'fake') {
    return { Icon: Cross, text: VERDICT_META.fake.label, ...pillFor('fake') };
  }
  if (verdict === 'real') {
    return { Icon: Check, text: VERDICT_META.real.label, ...pillFor('real') };
  }
  return {
    Icon: WarningIcon,
    text: VERDICT_META.uncertain.label,
    ...pillFor('uncertain'),
  };
}

function pillFor(verdict: Verdict): { tile: string; pill: string } {
  return { tile: VERDICT_META[verdict].pill, pill: VERDICT_META[verdict].pill };
}

// Solo los archivos PDF se incrustan con el visor; .txt/.md muestran su texto.
export function isPdfFilename(name?: string | null): boolean {
  return Boolean(name && name.toLowerCase().endsWith('.pdf'));
}

// Resumen "a favor / en contra" de las fuentes de una afirmación, en orden.
export const STANCE_SUMMARY_META = [
  { key: 'supports', label: 'a favor', dot: VERDICT_META.real.solid },
  { key: 'contradicts', label: 'en contra', dot: VERDICT_META.fake.solid },
  {
    key: 'inconclusive',
    label: 'no concluyente',
    dot: VERDICT_META.uncertain.solid,
  },
] as const;

// Postura de una fuente sobre la afirmación que tiene enlazada.
export function getStanceInfo(
  stance: string | null | undefined
): { text: string; className: string } | null {
  if (stance === 'supports') {
    return { text: 'Respalda', className: VERDICT_META.real.pill };
  }
  if (stance === 'contradicts') {
    return { text: 'Contradice', className: VERDICT_META.fake.pill };
  }
  if (stance === 'inconclusive') {
    return { text: 'No concluyente', className: VERDICT_META.uncertain.pill };
  }
  return null;
}
