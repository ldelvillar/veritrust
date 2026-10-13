import type { ReactNode } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DemoForm from './DemoForm';

const submit = vi.fn().mockResolvedValue(true);

vi.mock('@/hooks/useContactSubmission', () => ({
  useContactSubmission: () => ({ submit, isLoading: false, error: null }),
}));

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText(/Nombre/), {
    target: { value: 'Ana Pérez' },
  });
  fireEvent.change(screen.getByLabelText(/Email profesional/), {
    target: { value: 'ana@medio.es' },
  });
  fireEvent.change(screen.getByLabelText(/Organización/), {
    target: { value: 'Diario Salud' },
  });
  fireEvent.click(screen.getByDisplayValue('periodismo'));
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.submit(screen.getByRole('button', { name: /Solicitar/ }));
}

describe('DemoForm', () => {
  afterEach(() => {
    submit.mockClear();
    window.history.pushState({}, '', '/demo');
  });

  it('marks a lead that came from the Pro early access button', async () => {
    window.history.pushState({}, '', '/demo?plan=pro');
    render(<DemoForm />);

    fillAndSubmit();

    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    expect(submit.mock.calls[0][0].metadata).toMatchObject({
      Interés: 'Plan Pro (acceso anticipado)',
    });
  });

  it('marks a lead that came from the Equipo early access button', async () => {
    window.history.pushState({}, '', '/demo?plan=equipo');
    render(<DemoForm />);

    fillAndSubmit();

    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    expect(submit.mock.calls[0][0].metadata).toMatchObject({
      Interés: 'Plan Equipo (acceso anticipado)',
    });
  });

  it.each(['/demo', '/demo?plan=toString'])('leaves %s unmarked', async url => {
    window.history.pushState({}, '', url);
    render(<DemoForm />);

    fillAndSubmit();

    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    expect(submit.mock.calls[0][0].metadata).not.toHaveProperty('Interés');
  });
});
