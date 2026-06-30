import { useEffect, useRef } from 'react';

type CompletionStatus = 'done' | 'failed';

const NOTIFICATION_COPY: Record<
  CompletionStatus,
  { title: string; body: string }
> = {
  done: {
    title: 'Análisis completado',
    body: 'Tu informe ya está listo. Pulsa para verlo.',
  },
  failed: {
    title: 'El análisis ha fallado',
    body: 'No pudimos completar el análisis. Pulsa para reintentarlo.',
  },
};

function notificationsSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window;
}

// Avisa con una notificación del navegador cuando un análisis en curso termina
// con la pestaña en segundo plano; en primer plano la página ya se actualiza sola.
export function useCompletionNotification(id: string, status: string): void {
  const previousStatus = useRef(status);

  useEffect(() => {
    const previous = previousStatus.current;
    previousStatus.current = status;

    if (previous !== 'pending') return;
    if (status !== 'done' && status !== 'failed') return;
    if (!notificationsSupported() || Notification.permission !== 'granted') {
      return;
    }
    if (document.visibilityState !== 'hidden') return;

    const { title, body } = NOTIFICATION_COPY[status];
    const notification = new Notification(title, {
      body,
      icon: '/images/logo-192x192.png',
      tag: `veritrust-analysis-${id}`,
    });
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  }, [id, status]);
}
