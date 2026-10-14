import PlusIcon from '@/assets/Plus';
import { container } from './container';

export const faqEntries = [
  {
    q: '¿Qué es un detector de noticias falsas de salud?',
    a: (
      <>
        Es una herramienta que analiza contenido sanitario —texto, enlaces o
        documentos— y estima su credibilidad contrastando cada afirmación con la
        literatura científica. <strong>VeriTrust</strong> lo hace con un sistema
        multiagente de IA y cita las fuentes utilizadas, para que el resultado
        sea verificable.
      </>
    ),
    plain:
      'Es una herramienta que analiza contenido sanitario (texto, enlaces o documentos) y estima su credibilidad contrastando cada afirmación con la literatura científica. VeriTrust lo hace con un sistema multiagente de IA y cita las fuentes utilizadas.',
    open: true,
  },
  {
    q: '¿Cómo detecta VeriTrust los bulos médicos?',
    a: (
      <>
        Varios agentes trabajan en cadena: un <strong>extractor</strong> aísla
        las afirmaciones, un <strong>traductor</strong> normaliza el idioma y la
        terminología clínica, y un <strong>investigador</strong> busca evidencia
        en PubMed, Europe PMC y openFDA (y en CIMA, de la AEMPS, si se nombra un
        medicamento) y valora si cada fuente respalda o contradice la
        afirmación. Una regla fija decide el veredicto a partir de esas
        valoraciones y un <strong>experto en salud</strong> lo explica.
      </>
    ),
    plain:
      'Varios agentes de IA trabajan en cadena: un extractor aísla las afirmaciones, un traductor normaliza el idioma y la terminología clínica, y un investigador busca evidencia en PubMed, Europe PMC y openFDA (y en CIMA, de la AEMPS, si se nombra un medicamento) y valora si cada fuente respalda o contradice la afirmación. Una regla fija decide el veredicto y un experto en salud lo explica.',
    open: false,
  },
  {
    q: '¿Qué formatos de contenido puedo analizar?',
    a: (
      <>
        Puedes pegar <strong>texto</strong>, introducir un{' '}
        <strong>enlace</strong> (URL de un artículo) o subir un{' '}
        <strong>archivo</strong>: PDF, TXT o MD. El plan Gratis incluye texto y
        enlaces; los archivos, el plan Pro.
      </>
    ),
    plain:
      'Texto pegado, enlaces (URL de artículos) y archivos: PDF, TXT o MD. El plan Gratis incluye texto y enlaces; los archivos, el plan Pro.',
    open: false,
  },
  {
    q: '¿Cuál es la precisión de la herramienta?',
    a: (
      <>
        En 50 afirmaciones de salud ya verificadas por fact-checkers y
        autoridades sanitarias, que no usamos para ajustar el sistema, VeriTrust
        dio un veredicto firme en 32 y acertó en 29 (91 %). Nunca dio por
        verdadera una afirmación falsa. En las otras 18 respondió{' '}
        <strong>«Dudoso»</strong>, sobre todo con remedios caseros que la
        literatura científica no estudia. Puede equivocarse: revisa las fuentes
        de cada afirmación antes de publicar o difundir un resultado.
      </>
    ),
    plain:
      'En 50 afirmaciones de salud ya verificadas por fact-checkers y autoridades sanitarias, que no usamos para ajustar el sistema, VeriTrust dio un veredicto firme en 32 y acertó en 29 (91 %). Nunca dio por verdadera una afirmación falsa. En las otras 18 respondió «Dudoso», sobre todo con remedios caseros que la literatura científica no estudia. Puede equivocarse: revisa las fuentes de cada afirmación antes de publicar o difundir un resultado.',
    open: false,
  },
  {
    q: '¿Mis datos y los de mi organización están seguros?',
    a: (
      <>
        Sí. El contenido solo se usa para generar tu informe y mostrarlo en tu
        historial, y <strong>no se utiliza para entrenar modelos</strong>. Con
        las organizaciones firmamos un acuerdo de tratamiento de datos.
      </>
    ),
    plain:
      'El contenido solo se usa para generar tu informe y mostrarlo en tu historial, y no se utiliza para entrenar modelos. Con las organizaciones firmamos un acuerdo de tratamiento de datos.',
    open: false,
  },
  {
    q: '¿Hay una versión gratuita?',
    a: (
      <>
        Sí. El plan <strong>Gratis</strong> incluye 10 análisis al mes de{' '}
        <strong>texto y enlaces</strong> con el sistema completo, sin necesidad
        de tarjeta.
      </>
    ),
    plain:
      'Sí. El plan Gratis incluye 10 análisis al mes de texto y enlaces con el sistema completo, sin necesidad de tarjeta.',
    open: false,
  },
];

export default function Faq() {
  return (
    <section id="faq" className="bg-surface py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-sm font-extrabold tracking-[0.12em] text-primary uppercase">
            Preguntas frecuentes
          </span>
          <h2 className="my-4 font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md">
            Todo sobre el detector de noticias falsas de salud
          </h2>
        </div>
        <div className="mx-auto flex max-w-195 flex-col gap-3.5">
          {faqEntries.map(item => (
            <details
              key={item.q}
              open={item.open}
              className="group overflow-hidden rounded-2xl border border-line bg-white shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]"
            >
              <summary className="flex cursor-pointer list-none items-center gap-4 px-6 py-5.5 text-lg font-semibold text-ink [&::-webkit-details-marker]:hidden">
                <span className="flex-1">{item.q}</span>
                <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-surface text-primary transition group-open:rotate-45 group-open:bg-primary group-open:text-white">
                  <PlusIcon className="size-3.5" />
                </span>
              </summary>
              <div className="px-6 pb-6 text-sm leading-relaxed text-muted [&_strong]:font-bold [&_strong]:text-body">
                {item.a}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
