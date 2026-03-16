'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const closeMenu = () => setIsMenuOpen(false);

  useEffect(() => {
    if (!isMenuOpen) {
      document.body.style.overflow = '';
      return;
    }

    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = '';
    };
  }, [isMenuOpen]);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-white/95 px-4 py-3 backdrop-blur-sm md:px-6 md:py-4">
      <nav className="mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4 md:gap-10">
          <Link
            href="/"
            className="mr-2 flex items-center gap-2"
            onClick={closeMenu}
          >
            <Image
              src="/images/logo.webp"
              alt="Logo de VeriTrust"
              width={20}
              height={20}
            />
            <p className="text-lg font-semibold">VeriTrust</p>
          </Link>

          <div className="hidden items-center gap-8 md:flex">
            <Link
              href="/dashboard"
              className="transition duration-200 hover:text-primary"
            >
              Dashboard
            </Link>
            <Link
              href="/historial"
              className="transition duration-200 hover:text-primary"
            >
              Historial
            </Link>
            <Link
              href="/ayuda"
              className="transition duration-200 hover:text-primary"
            >
              Ayuda
            </Link>
          </div>
        </div>

        <div className="hidden items-center gap-5 md:flex">
          <Link
            href="/login"
            className="transition duration-200 hover:text-primary"
          >
            <p>Iniciar sesión</p>
          </Link>
          <Link
            href="/registro"
            className="rounded-lg bg-primary px-4 py-2 text-white transition duration-200 hover:bg-primary/90"
          >
            <p>Registrarse</p>
          </Link>
        </div>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-sm font-medium transition hover:bg-gray-100 md:hidden"
          aria-expanded={isMenuOpen}
          aria-controls="mobile-nav"
          aria-label="Abrir menú de navegación"
          onClick={() => setIsMenuOpen(prev => !prev)}
        >
          {isMenuOpen ? 'Cerrar' : 'Menú'}
        </button>
      </nav>

      {isMenuOpen && (
        <div
          id="mobile-nav"
          className="fixed inset-0 z-70 flex h-dvh min-h-screen flex-col overflow-y-auto bg-white px-4 pt-6 pb-6 md:hidden"
        >
          <div className="mb-5 flex items-center justify-between border-b border-border pb-4">
            <Link
              href="/"
              className="flex items-center gap-2"
              onClick={closeMenu}
            >
              <Image
                src="/images/logo.webp"
                alt="Logo de VeriTrust"
                width={20}
                height={20}
              />
              <p>VeriTrust</p>
            </Link>
            <button
              type="button"
              className="rounded-md border border-border px-3 py-2 text-sm font-medium transition hover:bg-gray-100"
              aria-label="Cerrar menú"
              onClick={closeMenu}
            >
              Cerrar
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-3">
            <Link
              href="/dashboard"
              className="rounded-md px-2 py-1 transition duration-200 hover:bg-gray-100 hover:text-primary"
              onClick={closeMenu}
            >
              Dashboard
            </Link>
            <Link
              href="/historial"
              className="rounded-md px-2 py-1 transition duration-200 hover:bg-gray-100 hover:text-primary"
              onClick={closeMenu}
            >
              Historial
            </Link>
            <Link
              href="/ayuda"
              className="rounded-md px-2 py-1 transition duration-200 hover:bg-gray-100 hover:text-primary"
              onClick={closeMenu}
            >
              Ayuda
            </Link>
            <div className="mt-1 flex flex-col gap-2 border-t border-border pt-3">
              <Link
                href="/login"
                className="rounded-md px-2 py-1 transition duration-200 hover:bg-gray-100 hover:text-primary"
                onClick={closeMenu}
              >
                Iniciar sesión
              </Link>
              <Link
                href="/registro"
                className="w-fit rounded-lg bg-primary px-4 py-2 text-white transition duration-200 hover:bg-primary/90"
                onClick={closeMenu}
              >
                Registrarse
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
