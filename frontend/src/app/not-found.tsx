'use client';

import { useEffect } from 'react';
import Link from 'next/link';

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
    <div className="animate-fade-in flex min-h-screen items-center justify-center p-4 text-white">
      <div className="relative z-10 max-w-md space-y-8 text-center">
        <h1 className="bg-linear-to-b from-primary to-[#1d0029] bg-clip-text text-9xl font-black text-transparent drop-shadow-lg">
          404
        </h1>

        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-gray-800 md:text-4xl">
            Página No Encontrada
          </h2>
          <p className="text-lg text-gray-500">
            Parece que esta página se perdió en el camino. Veamos dónde estamos.
          </p>
        </div>

        <div className="flex flex-col justify-center gap-4 sm:flex-row">
          <Link
            href="/"
            className="transform rounded-lg bg-primary px-8 py-3 font-bold transition-all duration-300 hover:scale-105 hover:bg-primary/90"
          >
            Ir a la página principal
          </Link>
          <button
            onClick={() => window.history.back()}
            className="rounded-lg border border-primary/30 bg-[#332938] px-8 py-3 font-bold transition-all duration-300 hover:bg-[#3a303d]"
          >
            Volver a la página anterior
          </button>
        </div>

        <p className="text-xs text-gray-400">
          Error 404 • La página que buscas no existe
        </p>
      </div>
    </div>
  );
}
