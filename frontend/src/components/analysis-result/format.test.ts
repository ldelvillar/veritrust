import { describe, expect, it } from 'vitest';
import { formatDuration } from './format';

describe('formatDuration', () => {
  it('redondea a minutos los análisis que pasan del minuto', () => {
    expect(
      formatDuration('2026-06-13T10:52:00.000Z', '2026-06-13T10:55:00.000Z')
    ).toBe('3 min');
  });

  it('usa segundos por debajo del minuto', () => {
    expect(
      formatDuration('2026-06-13T10:52:00.000Z', '2026-06-13T10:52:42.000Z')
    ).toBe('42 s');
  });

  it('no informa duración sin fecha de fin (informes antiguos)', () => {
    expect(formatDuration('2026-06-13T10:52:00.000Z', null)).toBeNull();
    expect(formatDuration('2026-06-13T10:52:00.000Z')).toBeNull();
  });

  it('descarta un fin anterior al inicio o una fecha inválida', () => {
    expect(
      formatDuration('2026-06-13T10:55:00.000Z', '2026-06-13T10:52:00.000Z')
    ).toBeNull();
    expect(
      formatDuration('2026-06-13T10:52:00.000Z', 'no-es-fecha')
    ).toBeNull();
  });
});
