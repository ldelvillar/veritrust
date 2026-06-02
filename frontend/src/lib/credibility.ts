export type Verdict = 'real' | 'fake' | 'uncertain';

export function classifyVerdict(label: string | null | undefined): Verdict {
  const l = (label ?? '').toLowerCase();
  if (l.includes('verdadera') || l.includes('real') || l.includes('true')) {
    return 'real';
  }
  if (l.includes('falsa') || l.includes('fake') || l.includes('false')) {
    return 'fake';
  }
  return 'uncertain';
}
