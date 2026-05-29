import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto w-full max-w-6xl px-4 md:px-6">
        <div className="mb-8 grid justify-items-center gap-8 text-center md:grid-cols-3 md:gap-6">
          <Link
            href="/aviso-legal"
            className="text-gray-600 transition duration-200 hover:text-primary"
          >
            Aviso legal
          </Link>
          <Link
            href="/terminos-y-condiciones"
            className="text-gray-600 transition duration-200 hover:text-primary"
          >
            Términos y condiciones
          </Link>
          <Link
            href="/politica-de-privacidad"
            className="text-gray-600 transition duration-200 hover:text-primary"
          >
            Política de privacidad
          </Link>
        </div>

        <p className="text-center text-gray-600">
          © 2026 VeriTrust. Todos los derechos reservados.
        </p>
      </div>
    </footer>
  );
}
