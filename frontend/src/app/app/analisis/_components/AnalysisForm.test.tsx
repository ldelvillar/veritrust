import type { ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PlanResponse } from '@/lib/plan';
import AnalysisForm from './AnalysisForm';

const submit = vi.fn();
let plan: PlanResponse | null = null;

vi.mock('@/hooks/usePlan', () => ({
  usePlan: () => ({
    plan,
    limits: plan?.limits ?? null,
    usage: plan?.usage ?? null,
  }),
}));

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

function freePlan(remaining: number): PlanResponse {
  return {
    plan: 'free',
    status: null,
    interval: null,
    current_period_end: null,
    cancel_at: null,
    limits: {
      name: 'free',
      analyses_per_month: 10,
      max_input_chars: 3000,
      history_days: 30,
      files: false,
      history_tools: false,
      dashboard: false,
      csv_export: false,
      share: false,
      mcp: false,
      pdf: false,
    },
    usage: {
      used: 10 - remaining,
      pending: 0,
      remaining,
      resets_at: '2026-10-31T23:00:00Z',
    },
  };
}

vi.mock('@/hooks/useAnalysisSubmission', () => ({
  useAnalysisSubmission: () => ({
    submit,
    submitFile: vi.fn(),
    isLoading: false,
    error: null,
    setError: vi.fn(),
  }),
}));

const HINT = 'Escribe un dominio completo, p. ej. medio.es';
const URL_LABEL = 'Introduce la URL del artículo';
const TEXT_LABEL = 'Pega el texto o la afirmación a verificar';
const RUN_BUTTON = 'Analizar credibilidad';

const LIMITS = {
  max_file_bytes: 10 * 1024 * 1024,
  allowed_file_suffixes: ['.md', '.pdf', '.txt'],
  min_input_text_length: 10,
  max_input_text_length: 10_000,
};

function typeUrl(value: string) {
  fireEvent.click(screen.getByRole('tab', { name: 'Enlace' }));
  fireEvent.change(screen.getByLabelText(URL_LABEL), { target: { value } });
}

function typeText(value: string) {
  fireEvent.change(screen.getByLabelText(TEXT_LABEL), { target: { value } });
}

beforeEach(() => {
  submit.mockClear();
  plan = null;
});

describe('AnalysisForm URL validation', () => {
  it('blocks a link without a real domain', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeUrl('hola');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(screen.getByLabelText(URL_LABEL)).toHaveAttribute(
      'aria-invalid',
      'true'
    );
  });

  it('accepts a link with a real domain', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeUrl('www.medio.es/salud/articulo');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeEnabled();
    expect(screen.queryByText(HINT)).toBeNull();
  });

  it('does not submit an invalid link on Enter', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeUrl('hola');
    fireEvent.keyDown(screen.getByLabelText(URL_LABEL), { key: 'Enter' });

    expect(submit).not.toHaveBeenCalled();
  });

  it('submits a valid link on Enter', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeUrl('www.medio.es/salud/articulo');
    fireEvent.keyDown(screen.getByLabelText(URL_LABEL), { key: 'Enter' });

    expect(submit).toHaveBeenCalledWith({
      url: 'https://www.medio.es/salud/articulo',
      source_type: 'url',
    });
  });
});

describe('AnalysisForm text limits from GET /config', () => {
  it('blocks text shorter than the minimum the API publishes', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeText('corto');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
  });

  it('accepts text once it clears the published minimum', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeText('La vitamina C previene el resfriado');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeEnabled();
  });

  it('blocks text longer than the maximum the API publishes', () => {
    render(<AnalysisForm limits={LIMITS} />);
    typeText('a'.repeat(LIMITS.max_input_text_length + 1));

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
  });

  it('defers to the server when the limits could not be loaded', () => {
    render(<AnalysisForm limits={null} />);
    typeText('corto');

    // Without limits the length is not prevalidated, so the submit goes through and the API decides.
    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeEnabled();
    expect(screen.queryByText(/mínimo/)).toBeNull();
  });
});

describe('AnalysisForm limits from the Plan', () => {
  it('caps pasted text at the Free plan maximum, below the schema one', () => {
    plan = freePlan(5);
    render(<AnalysisForm limits={LIMITS} />);
    typeText('a'.repeat(3001));

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
    expect(
      screen.getByText(/supera el máximo de 3\.000 caracteres del plan Gratis/)
    ).toBeInTheDocument();
  });

  it('shows the upsell instead of the file picker on the Free plan', () => {
    plan = freePlan(5);
    render(<AnalysisForm limits={LIMITS} />);
    fireEvent.click(screen.getByRole('tab', { name: /Archivo/ }));

    expect(screen.getByText('Analiza archivos con Pro')).toBeInTheDocument();
    expect(screen.queryByText(/Arrastra un archivo/)).toBeNull();
  });

  it('tells a Free user how much of a page is analysed', () => {
    plan = freePlan(5);
    render(<AnalysisForm limits={LIMITS} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Enlace' }));

    expect(
      screen.getByText(/se analizan los primeros 3\.000 caracteres/)
    ).toBeInTheDocument();
  });

  it('blocks submitting once the Allowance is used up', () => {
    plan = freePlan(0);
    render(<AnalysisForm limits={LIMITS} />);
    typeText('La vitamina C previene el resfriado');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
    expect(
      screen.getByText('Has usado tus análisis de este mes')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Se renuevan el 1 de noviembre/)
    ).toBeInTheDocument();
  });

  it('does not submit on Enter once the Allowance is used up', () => {
    plan = freePlan(0);
    render(<AnalysisForm limits={LIMITS} />);
    typeText('La vitamina C previene el resfriado');
    fireEvent.keyDown(screen.getByLabelText(TEXT_LABEL), { key: 'Enter' });

    expect(submit).not.toHaveBeenCalled();
  });

  it('does not submit on Enter a text over the plan maximum', () => {
    plan = freePlan(5);
    render(<AnalysisForm limits={LIMITS} />);
    typeText('a'.repeat(3001));
    fireEvent.keyDown(screen.getByLabelText(TEXT_LABEL), { key: 'Enter' });

    expect(submit).not.toHaveBeenCalled();
  });
});
