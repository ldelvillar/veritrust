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
const RUN_BUTTON = 'Analizar credibilidad';

function typeUrl(value: string) {
  fireEvent.click(screen.getByRole('tab', { name: 'Enlace' }));
  fireEvent.change(screen.getByLabelText(URL_LABEL), { target: { value } });
}

describe('AnalysisForm URL validation', () => {
  beforeEach(() => {
    submit.mockClear();
  });

  it('blocks a link without a real domain', () => {
    render(<AnalysisForm />);
    typeUrl('hola');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeDisabled();
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(screen.getByLabelText(URL_LABEL)).toHaveAttribute(
      'aria-invalid',
      'true'
    );
  });

  it('accepts a link with a real domain', () => {
    render(<AnalysisForm />);
    typeUrl('www.medio.es/salud/articulo');

    expect(screen.getByRole('button', { name: RUN_BUTTON })).toBeEnabled();
    expect(screen.queryByText(HINT)).toBeNull();
  });

  it('does not submit an invalid link on Enter', () => {
    render(<AnalysisForm />);
    typeUrl('hola');
    fireEvent.keyDown(screen.getByLabelText(URL_LABEL), { key: 'Enter' });

    expect(submit).not.toHaveBeenCalled();
  });

  it('submits a valid link on Enter', () => {
    render(<AnalysisForm />);
    typeUrl('www.medio.es/salud/articulo');
    fireEvent.keyDown(screen.getByLabelText(URL_LABEL), { key: 'Enter' });

    expect(submit).toHaveBeenCalledWith({
      url: 'https://www.medio.es/salud/articulo',
      source_type: 'url',
    });
  });
});
