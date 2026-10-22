import Link from 'next/link';

import Logo from '@/assets/Logo';
import Wordmark from '@/components/Wordmark';

export default function AuthShell({
  children,
  legalNotice = false,
}: Readonly<{ children: React.ReactNode; legalNotice?: boolean }>) {
  return (
    <main className="flex min-h-screen flex-col bg-surface-subtle bg-[radial-gradient(ellipse_80%_70%_at_50%_-10%,rgba(227,238,237,0.7),transparent)] px-5 py-5 md:px-8 md:py-7">
      <div className="flex items-center justify-between gap-3.5">
        <Link href="/" className="flex items-center gap-2.25">
          <Logo className="size-4.75" />
          <Wordmark className="text-2xl" />
        </Link>
        <Link
          href="/"
          className="text-xs font-semibold tracking-wider text-muted uppercase transition hover:text-primary"
        >
          ← Volver al inicio
        </Link>
      </div>
      <div className="flex flex-1 items-center justify-center py-5 md:py-8">
        {children}
      </div>
      {legalNotice && (
        <p className="text-center text-xs leading-normal text-faint">
          Al continuar aceptas los{' '}
          <Link
            href="/terminos-y-condiciones"
            className="text-muted hover:text-primary"
          >
            Términos
          </Link>{' '}
          y la{' '}
          <Link
            href="/politica-de-privacidad"
            className="text-muted hover:text-primary"
          >
            Política de privacidad
          </Link>
          .
        </p>
      )}
    </main>
  );
}
