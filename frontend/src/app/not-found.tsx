import type { Metadata } from 'next';
import Link from 'next/link';

import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import PublicButton from '@/components/PublicButton';
import BackButton from './_components/BackButton';

export const metadata: Metadata = {
  title: 'Página no encontrada (404)',
  description:
    'La página que buscas no existe o ha cambiado de dirección. Vuelve al inicio de VeriTrust o analiza un contenido médico gratis.',
};

const shortcuts = [
  { label: 'Cómo funciona', href: '/#como-funciona' },
  { label: 'Precios', href: '/#precios' },
  { label: 'Casos de uso', href: '/#casos' },
  { label: 'Contacto', href: '/contacto' },
];

export default function NotFoundPage() {
  return (
    <div className="relative flex min-h-screen flex-col bg-surface-subtle bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(227,238,237,0.5),rgba(255,255,255,0.9))]">
      <Header />
      <main className="flex flex-1 flex-col">
        <section
          aria-labelledby="nf-title"
          className="relative flex flex-1 items-center overflow-hidden bg-primary py-24 text-white max-[900px]:py-18"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_70%_at_88%_30%,rgba(255,255,255,0.09),transparent_70%)]" />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -right-7.5 -bottom-47.5 font-display text-[480px] leading-[0.8] tracking-[-0.02em] text-white/7 select-none max-[900px]:-right-5 max-[900px]:-bottom-32.5 max-[900px]:text-[340px] max-[600px]:opacity-60"
          >
            404
          </div>

          <div className="mx-auto w-full max-w-345 px-5 md:px-8">
            <div className="relative z-2 max-w-190">
              <div className="text-sm font-extrabold tracking-[0.12em] text-white/62 uppercase">
                Error 404 · Página no encontrada
              </div>
              <h1
                id="nf-title"
                className="mt-4.5 font-display text-display-lg font-normal tracking-[-0.012em] text-balance text-white max-[900px]:text-display-md max-[600px]:text-display-sm"
              >
                Esta dirección{' '}
                <em className="italic">no ha pasado la verificación</em>
              </h1>
              <p className="mt-5 max-w-140 text-lg leading-relaxed text-white/86">
                El enlace que has seguido no existe, ha cambiado de sitio o se
                copió incompleto. El resto de VeriTrust sigue en pie.
              </p>

              <div className="mt-9 mb-7.5 flex flex-wrap gap-3.5">
                <PublicButton href="/" variant="light" size="lg">
                  Ir al inicio
                </PublicButton>
                <BackButton />
              </div>

              <div className="flex flex-wrap items-center gap-x-5 gap-y-2.5 border-t border-white/16 pt-6.5">
                <b className="text-2xs font-extrabold tracking-[0.11em] text-white/50 uppercase">
                  O ve directamente a
                </b>
                {shortcuts.map(shortcut => (
                  <Link
                    key={shortcut.label}
                    href={shortcut.href}
                    className="text-sm font-semibold text-white/90 transition hover:text-white hover:underline hover:underline-offset-[3px]"
                  >
                    {shortcut.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
