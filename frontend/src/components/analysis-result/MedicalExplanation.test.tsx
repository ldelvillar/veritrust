import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import MedicalExplanation from './MedicalExplanation';

const EXPLANATION = 'La vitamina C **no previene** el resfriado común.';

function stubClipboard(writeText: () => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  });
}

describe('MedicalExplanation', () => {
  it('copies the raw explanation and confirms it', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubClipboard(writeText);

    render(<MedicalExplanation explanation={EXPLANATION} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }));

    expect(writeText).toHaveBeenCalledWith(EXPLANATION);
    expect(
      await screen.findByRole('button', { name: 'Copiado' })
    ).toBeInTheDocument();
  });

  it('reports a failed copy instead of confirming', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denegado'));
    stubClipboard(writeText);

    render(<MedicalExplanation explanation={EXPLANATION} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }));

    expect(
      await screen.findByRole('button', { name: 'No se pudo copiar' })
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Copiado' })).toBeNull();
  });
});
