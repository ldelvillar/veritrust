import { describe, expect, it } from 'vitest';
import { classifyVerdict } from './credibility';

describe('classifyVerdict', () => {
  it('classifies real, fake and uncertain labels', () => {
    expect(classifyVerdict('verdadera')).toBe('real');
    expect(classifyVerdict('Noticia falsa')).toBe('fake');
    expect(classifyVerdict('true')).toBe('real');
    expect(classifyVerdict('fake')).toBe('fake');
    expect(classifyVerdict('')).toBe('uncertain');
    expect(classifyVerdict(null)).toBe('uncertain');
  });
});
