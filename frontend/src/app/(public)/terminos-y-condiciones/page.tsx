import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Términos y condiciones | VeriTrust',
  description:
    'Revisa los términos y condiciones de uso de la plataforma VeriTrust.',
};

export default function TerminosYCondicionesPage() {
  return (
    <section className="animate-fade-in mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
      <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 md:text-5xl">
        Términos y condiciones
      </h1>
      <p className="mt-4 text-base leading-7 text-gray-600 md:text-lg">
        Estos términos regulan el acceso y uso de VeriTrust. Al utilizar
        nuestros servicios, aceptas estas condiciones en su totalidad.
      </p>

      <div className="mt-10 space-y-10">
        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            1. Objeto del servicio
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            VeriTrust proporciona herramientas de análisis de contenido médico
            para apoyar la identificación de posible desinformación. El servicio
            es de apoyo y no sustituye asesoramiento médico, legal ni
            profesional.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            2. Registro y cuenta
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Eres responsable de la veracidad de los datos aportados y de
            mantener la confidencialidad de tus credenciales. Toda actividad
            realizada desde tu cuenta se entenderá efectuada por ti.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">3. Uso permitido</h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            No está permitido utilizar la plataforma para actividades ilícitas,
            para difundir contenido ofensivo o para vulnerar derechos de
            propiedad intelectual y privacidad de terceros.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            4. Disponibilidad y cambios
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Podemos actualizar, modificar o suspender funcionalidades cuando sea
            necesario por motivos técnicos, de seguridad o de mejora del
            servicio, intentando minimizar el impacto en el usuario.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            5. Responsabilidad
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            No garantizamos que los resultados sean exactos al cien por cien en
            todos los casos. El usuario asume la responsabilidad de validar la
            información antes de tomar decisiones relevantes basadas en ella.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            6. Vigencia y modificaciones
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Estos términos pueden actualizarse periódicamente. Las nuevas
            versiones se publicarán en esta pagina y entrarán en vigor desde su
            publicación.
          </p>
        </section>
      </div>
    </section>
  );
}
