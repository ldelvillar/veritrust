import { useCallback, useState } from 'react';

import { ApiError } from '@/lib/apiClient';
import { refreshPlanOnPlanError } from '@/lib/planCache';

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

// State and error translation shared by every API mutation.
export function useApiMutation() {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Return the response, or null if the request failed and the message is in `error`.
  const mutate = useCallback(
    async <TResponse>(
      request: () => Promise<TResponse>
    ): Promise<TResponse | null> => {
      setError(null);
      setIsPending(true);
      try {
        return await request();
      } catch (err) {
        refreshPlanOnPlanError(err);
        setError(err instanceof ApiError ? err.message : CONNECTION_ERROR);
        return null;
      } finally {
        setIsPending(false);
      }
    },
    []
  );

  return { mutate, isPending, error, setError };
}
