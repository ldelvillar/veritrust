'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Show, SignInButton } from '@clerk/nextjs';
import Button from '@/components/Button';
import Logo from '@/assets/Logo';

const navLinks = [
  { href: '/#como-funciona', label: 'Cómo funciona' },
  { href: '/ejemplo', label: 'Ejemplo' },
  { href: '/#casos', label: 'Casos de uso' },
  { href: '/#precios', label: 'Precios' },
];

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  const closeMenu = () => setIsMenuOpen(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

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
    <header
      className={`sticky top-0 z-50 w-full border-b bg-white transition-[border-color,box-shadow] duration-200 ${
        scrolled
          ? 'border-border shadow-[0_4px_20px_rgba(40,30,90,0.05)]'
          : 'border-transparent'
      }`}
    >
      <nav
        aria-label="Principal"
        className="mx-auto flex h-18 w-full max-w-345 items-center gap-3.5 px-5 md:px-8"
      >
        <Link
          href="/"
          className="flex items-center gap-2.5"
          onClick={closeMenu}
        >
          <Logo className="h-6 w-auto" />
          <span className="text-[19px] font-bold tracking-[-0.02em] text-ink">
            VeriTrust
          </span>
        </Link>

        <div className="mx-auto hidden items-center gap-1.5 md:flex">
          {navLinks.map(link => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-[9px] px-3.5 py-2.5 text-[14.5px] font-semibold text-[#6f7090] transition hover:text-primary"
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-2.5 md:flex">
          <Show when="signed-out">
            <SignInButton forceRedirectUrl="/app/analisis">
              <button className="cursor-pointer px-3.5 py-2.5 text-[14.5px] font-bold text-body transition hover:text-primary">
                Iniciar sesión
              </button>
            </SignInButton>
          </Show>
          <Show when="signed-in">
            <Link
              href="/app/analisis"
              className="px-3.5 py-2.5 text-[14.5px] font-bold text-body transition hover:text-primary"
            >
              Ir a la app
            </Link>
          </Show>
          <Button href="/contacto">Contacto</Button>
        </div>

        <button
          type="button"
          className="ml-auto inline-flex items-center justify-center rounded-md border border-border px-3 py-2 text-sm font-medium transition hover:bg-surface md:hidden"
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
              className="flex items-center gap-2.5"
              onClick={closeMenu}
            >
              <Logo className="h-6 w-auto" />
              <span className="text-[19px] font-bold tracking-[-0.02em] text-ink">
                VeriTrust
              </span>
            </Link>
            <button
              type="button"
              className="rounded-md border border-border px-3 py-2 text-sm font-medium transition hover:bg-surface"
              aria-label="Cerrar menú"
              onClick={closeMenu}
            >
              Cerrar
            </button>
          </div>

          <div className="flex flex-1 flex-col gap-2">
            {navLinks.map(link => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-md px-2 py-2 font-semibold text-body transition duration-200 hover:bg-surface hover:text-primary"
                onClick={closeMenu}
              >
                {link.label}
              </Link>
            ))}

            <div className="mt-2 flex flex-col gap-2 border-t border-border pt-3">
              <Show when="signed-out">
                <SignInButton forceRedirectUrl="/app/analisis">
                  <button
                    className="h-11 cursor-pointer px-4 text-sm font-medium transition duration-300 hover:text-primary"
                    onClick={closeMenu}
                  >
                    Iniciar sesión
                  </button>
                </SignInButton>
              </Show>
              <Show when="signed-in">
                <Link
                  href="/app/analisis"
                  className="h-11 pt-2 text-center text-sm font-medium transition duration-300 hover:text-primary"
                  onClick={closeMenu}
                >
                  Ir a la app
                </Link>
              </Show>
              <Button
                href="/contacto"
                className="h-11 w-full"
                onClick={closeMenu}
              >
                Contacto
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
