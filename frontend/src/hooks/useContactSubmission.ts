'use client';

import { useState, useCallback } from 'react';

import { ApiError, postJsonPublic } from '@/lib/apiClient';
import type { components } from '@/types/api';

type ContactRequest = components['schemas']['ContactRequest'];
type ContactResponse = components['schemas']['ContactResponse'];

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

export function useContactSubmission() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (body: ContactRequest): Promise<boolean> => {
    setError(null);
    setIsLoading(true);
    try {
      await postJsonPublic<ContactResponse>('/contact', body);
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { submit, isLoading, error, setError };
}
