'use client';

import { useCallback } from 'react';

import { postJsonPublic } from '@/lib/apiClient';
import { useApiMutation } from '@/hooks/useApiMutation';
import type { components } from '@/types/api';

type ContactRequest = components['schemas']['ContactRequest'];
type ContactResponse = components['schemas']['ContactResponse'];

export function useContactSubmission() {
  const { mutate, isPending, error, setError } = useApiMutation();

  const submit = useCallback(
    async (body: ContactRequest): Promise<boolean> => {
      const data = await mutate(() =>
        postJsonPublic<ContactResponse>('/contact', body)
      );
      return data !== null;
    },
    [mutate]
  );

  return { submit, isLoading: isPending, error, setError };
}
