'use client';

import { useEffect } from 'react';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import Button from '@/components/Button';

export default function NotFoundPage() {
  useEffect(() => {
    document.title = '404 No Encontrado | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'La página que buscas no existe. Explora VeriTrust para descubrir más.'
      );
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col bg-surface-subtle bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(227,238,237,0.5),rgba(255,255,255,0.9))]">
      <Header />
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-20 text-center">
        <div className="animate-fade-in max-w-md space-y-8">
          <h1 className="bg-linear-to-b from-primary to-ink-deep bg-clip-text text-9xl font-black text-transparent">
            404
          </h1>

          <div className="space-y-2">
            <h2 className="text-3xl font-bold text-ink md:text-4xl">
              Página no encontrada
            </h2>
            <p className="text-lg text-muted">
              Parece que esta página se perdió en el camino. Volvamos a un lugar
              seguro.
            </p>
          </div>

          <div className="flex flex-col justify-center gap-3 sm:flex-row">
            <Button href="/" size="lg">
              Ir a la página principal
            </Button>
            <Button
              variant="soft"
              size="lg"
              onClick={() => window.history.back()}
            >
              Volver atrás
            </Button>
          </div>

          <p className="text-xs text-faint">
            Error 404 • La página que buscas no existe
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
