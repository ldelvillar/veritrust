import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AnalysisForm from './AnalysisForm';

const submit = vi.fn();

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

// Los límites llegan de GET /config.
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

describe('AnalysisForm URL validation', () => {
  beforeEach(() => {
    submit.mockClear();
  });

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
    expect(screen.getByText(/mínimo 10/)).toBeInTheDocument();
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

    // Sin límites no se prevalida la longitud: el envío llega y la API decide.
    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeEnabled();
    expect(screen.queryByText(/mínimo/)).toBeNull();
  });
});
