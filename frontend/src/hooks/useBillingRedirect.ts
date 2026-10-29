'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { useApiMutation } from '@/hooks/useApiMutation';
import { fetchJsonWithAuth } from '@/lib/apiClient';
import type { BillingInterval } from '@/lib/plan';
import type { components } from '@/types/api';

type BillingUrlResponse = components['schemas']['BillingUrlResponse'];

// Abre el Checkout o el portal de Stripe, que viven fuera de la app.
export function useBillingRedirect() {
  const { getToken } = useAuth();
  const { mutate, isPending, error } = useApiMutation();
  const [isRedirecting, setIsRedirecting] = useState(false);

  // Volver atrás desde Stripe puede restaurar la página de la bfcache con el botón aún ocupado.
  useEffect(() => {
    const reset = (event: PageTransitionEvent) => {
      if (event.persisted) setIsRedirecting(false);
    };
    window.addEventListener('pageshow', reset);
    return () => window.removeEventListener('pageshow', reset);
  }, []);

  const redirectTo = useCallback(
    async (path: string, body?: unknown) => {
      const data = await mutate(() =>
        fetchJsonWithAuth<BillingUrlResponse>(getToken, path, {
          method: 'POST',
          body,
        })
      );
      if (!data) return;
      // El botón sigue ocupado hasta que el navegador abandona la página.
      setIsRedirecting(true);
      window.location.assign(data.url);
    },
    [getToken, mutate]
  );

  const startCheckout = useCallback(
    (interval: BillingInterval) =>
      redirectTo('/billing/checkout', { interval }),
    [redirectTo]
  );

  const openPortal = useCallback(
    () => redirectTo('/billing/portal'),
    [redirectTo]
  );

  return {
    startCheckout,
    openPortal,
    isRedirecting: isPending || isRedirecting,
    error,
  };
}
