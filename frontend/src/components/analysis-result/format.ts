import Check from '@/assets/Check';
import Cross from '@/assets/Cross';
import WarningIcon from '@/assets/Warning';
import type { Verdict } from './types';

export function getVerdictInfo(verdict: Verdict): {
  text: string;
  description: string;
  band: string;
} {
  if (verdict === 'real') {
    return {
      text: 'Noticia verdadera',
      description:
        'El contenido muestra alta consistencia factual con fuentes médicas reputadas y bajos indicadores de información errónea.',
      band: 'linear-gradient(135deg,#2bc488,#10a566 70%,#0c9059)',
    };
  }
  if (verdict === 'fake') {
    return {
      text: 'Noticia falsa',
      description:
        'El contenido contiene afirmaciones que contradicen o no pueden ser verificadas con fuentes médicas reconocidas.',
      band: 'linear-gradient(135deg,#e2607a,#d23c5d 70%,#c33051)',
    };
  }
  return {
    text: 'Resultado incierto',
    description:
      'No se ha podido determinar con certeza la veracidad del contenido. Se recomienda consultar fuentes adicionales.',
    band: 'linear-gradient(135deg,#e8b057,#d98e29 70%,#c97e1c)',
  };
}

export function normalizeFraction(value: number): number {
  return value <= 1 ? value : value / 100;
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
    return {
      Icon: Cross,
      text: 'Falsa',
      tile: 'bg-red-50 text-red-700',
      pill: 'bg-red-50 text-red-700',
    };
  }
  if (verdict === 'real') {
    return {
      Icon: Check,
      text: 'Verdadera',
      tile: 'bg-emerald-50 text-emerald-700',
      pill: 'bg-emerald-50 text-emerald-700',
    };
  }
  return {
    Icon: WarningIcon,
    text: 'Dudosa',
    tile: 'bg-amber-50 text-amber-700',
    pill: 'bg-amber-50 text-amber-700',
  };
}

// Solo los archivos PDF se incrustan con el visor; .txt/.md muestran su texto.
export function isPdfFilename(name?: string | null): boolean {
  return Boolean(name && name.toLowerCase().endsWith('.pdf'));
}
