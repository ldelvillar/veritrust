import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { HelpArticle, HelpFaqItem } from '../helpContent';
import HelpSearch from './HelpSearch';

const articles = [
  {
    id: 'leer-la-puntuacion',
    category: 'Cómo leer un informe',
    title: 'Leer la puntuación',
    summary:
      'La puntuación resume la credibilidad del contenido en una escala de 0 a 100.',
    tags: ['Puntuación', 'Credibilidad'],
  },
  {
    id: 'fuentes-medicas',
    category: 'Fuentes y metodología',
    title: 'Fuentes médicas',
    summary:
      'VeriTrust prioriza organismos sanitarios y literatura biomédica reconocida.',
    tags: ['OMS', 'Cochrane'],
  },
  {
    id: 'falsos-positivos',
    category: 'Solución de problemas',
    title: 'Falsos positivos',
    summary:
      'Revisa si faltaba contexto o el texto mezclaba varias afirmaciones.',
    tags: ['Veredicto', 'Contexto'],
  },
] satisfies HelpArticle[];

const faq = [
  {
    cat: 'Uso',
    q: '¿Cuánto tarda un análisis?',
    a: 'La mayoría de análisis se completan en 30–60 segundos.',
  },
] satisfies HelpFaqItem[];

function renderHelpSearch(popular = ['Falsos positivos']) {
  render(<HelpSearch articles={articles} faq={faq} popular={popular} />);
}

describe('HelpSearch', () => {
  it('filters articles without requiring accents', async () => {
    const user = userEvent.setup();
    renderHelpSearch();

    await user.type(
      screen.getByLabelText('Buscar en el centro de ayuda'),
      'puntuacion'
    );

    expect(
      screen.getByRole('link', { name: /Leer la puntuación/i })
    ).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Fuentes médicas/i })).toBeNull();
  });

  it('searches FAQ content', async () => {
    const user = userEvent.setup();
    renderHelpSearch();

    await user.type(
      screen.getByLabelText('Buscar en el centro de ayuda'),
      '30 segundos'
    );

    expect(
      screen.getByRole('link', { name: /¿Cuánto tarda un análisis\?/i })
    ).toBeInTheDocument();
  });

  it('uses popular terms to populate the query', async () => {
    const user = userEvent.setup();
    renderHelpSearch();
    const input = screen.getByLabelText('Buscar en el centro de ayuda');

    await user.click(screen.getByRole('button', { name: 'Falsos positivos' }));

    expect(input).toHaveValue('Falsos positivos');
    expect(
      screen.getByRole('link', { name: /Falsos positivos/i })
    ).toBeInTheDocument();
  });

  it('shows an empty result message', async () => {
    const user = userEvent.setup();
    renderHelpSearch();

    await user.type(
      screen.getByLabelText('Buscar en el centro de ayuda'),
      'sin resultado'
    );

    expect(
      screen.getByText('No hay resultados para «sin resultado».')
    ).toBeInTheDocument();
  });
});
