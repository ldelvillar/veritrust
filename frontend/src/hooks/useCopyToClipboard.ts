import { useCallback, useEffect, useRef, useState } from 'react';

export type CopyState = 'idle' | 'copied' | 'error';

export const COPY_LABEL: Record<CopyState, string> = {
  idle: 'Copiar',
  copied: 'Copiado',
  error: 'No se pudo copiar',
};

const RESET_MS = 2000;

export function useCopyToClipboard() {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const reset = useCallback(() => {
    clearTimeout(timer.current);
    setState('idle');
  }, []);

  const copy = useCallback(async (text: string) => {
    clearTimeout(timer.current);
    try {
      await navigator.clipboard.writeText(text);
      setState('copied');
    } catch {
      setState('error');
    }
    timer.current = setTimeout(() => setState('idle'), RESET_MS);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);

  return { state, copy, reset };
}
