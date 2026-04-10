import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Ayuda | VeriTrust',
  description:
    'Centro de ayuda de VeriTrust con guia de uso, preguntas frecuentes y soporte.',
};

export default function AyudaPage() {
  return (
    <section className="animate-fade-in mx-auto w-full max-w-5xl px-4 py-12 md:py-16">
      <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 md:text-5xl">
        Centro de ayuda
      </h1>
      <p className="mt-4 max-w-3xl text-base leading-7 text-gray-600 md:text-lg">
        Encuentra respuestas rapidas para usar VeriTrust: como analizar
        contenido, interpretar resultados y gestionar tu historial.
      </p>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        <Link
          href="/"
          className="rounded-2xl border border-border bg-white p-5 shadow-sm transition duration-200 hover:border-primary/40"
        >
          <h2 className="text-lg font-bold text-gray-900">Nuevo analisis</h2>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            Ve a la pagina principal para pegar texto, subir archivo o analizar
            una URL.
          </p>
        </Link>

        <Link
          href="/historial"
          className="rounded-2xl border border-border bg-white p-5 shadow-sm transition duration-200 hover:border-primary/40"
        >
          <h2 className="text-lg font-bold text-gray-900">Historial</h2>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            Filtra por tipo, fecha, puntuacion o busqueda para localizar
            analisis anteriores.
          </p>
        </Link>

        <Link
          href="/dashboard"
          className="rounded-2xl border border-border bg-white p-5 shadow-sm transition duration-200 hover:border-primary/40"
        >
          <h2 className="text-lg font-bold text-gray-900">Dashboard</h2>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            Revisa un resumen general de actividad y rendimiento de tus
            verificaciones.
          </p>
        </Link>
      </div>

      <div className="mt-12 space-y-8">
        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            Preguntas frecuentes
          </h2>
          <div className="mt-5 space-y-4">
            <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
              <h3 className="text-base font-bold text-gray-900">
                Como interpreto la puntuacion de credibilidad?
              </h3>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                La puntuacion va de 0 a 100. Cuanto mas alta es, mayor confianza
                ofrece el sistema en la credibilidad del contenido analizado.
                Aun asi, siempre conviene contrastar con fuentes confiables.
              </p>
            </article>

            <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
              <h3 className="text-base font-bold text-gray-900">
                Por que no veo resultados en el historial?
              </h3>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Revisa los filtros activos de busqueda, tipo o rango de fechas.
                Si no coinciden con tus registros, la tabla puede aparecer vacia
                aunque tengas analisis guardados.
              </p>
            </article>

            <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
              <h3 className="text-base font-bold text-gray-900">
                Puedo usar el resultado como diagnostico medico?
              </h3>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                No. VeriTrust es una herramienta de apoyo para detectar posible
                desinformacion. No sustituye el criterio de profesionales
                sanitarios ni de fuentes oficiales.
              </p>
            </article>
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-bold text-gray-900">
            Contacto y soporte
          </h2>
          <p className="mt-3 text-sm leading-6 text-gray-600 md:text-base">
            Si tienes dudas tecnicas, errores recurrentes o sugerencias para
            mejorar la plataforma, puedes escribirnos y te responderemos lo
            antes posible.
          </p>
          <a
            href="mailto:lucasvillarv@gmail.com"
            className="mt-4 inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition duration-200 hover:bg-primary/90"
          >
            Contactar por correo
          </a>
        </section>
      </div>
    </section>
  );
}
