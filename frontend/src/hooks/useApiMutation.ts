import { useCallback, useState } from 'react';

import { ApiError } from '@/lib/apiClient';

const CONNECTION_ERROR =
  'Sin conexión con el servidor. Comprueba tu conexión e inténtalo de nuevo.';

// Estado y traducción de errores que comparten todas las mutaciones de la API.
export function useApiMutation() {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Devuelve la respuesta, o null si la petición falló y el mensaje quedó en `error`.
  const mutate = useCallback(
    async <TResponse>(
      request: () => Promise<TResponse>
    ): Promise<TResponse | null> => {
      setError(null);
      setIsPending(true);
      try {
        return await request();
      } catch (err) {
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
