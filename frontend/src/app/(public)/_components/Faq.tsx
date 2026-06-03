import PlusIcon from '@/assets/Plus';
import { container } from './container';

export const faqEntries = [
  {
    q: '¿Qué es un detector de noticias falsas de salud?',
    a: (
      <>
        Es una herramienta que analiza contenido sanitario —texto, enlaces o
        documentos— y estima su credibilidad contrastando cada afirmación con el
        consenso médico. <strong>VeriTrust</strong> lo hace con un sistema
        multiagente de IA y cita las fuentes utilizadas, para que el resultado
        sea verificable.
      </>
    ),
    plain:
      'Es una herramienta que analiza contenido sanitario (texto, enlaces o documentos) y estima su credibilidad contrastando cada afirmación con el consenso médico. VeriTrust lo hace con un sistema multiagente de IA y cita las fuentes utilizadas.',
    open: true,
  },
  {
    q: '¿Cómo detecta VeriTrust los bulos médicos?',
    a: (
      <>
        Tres agentes trabajan en cadena: un <strong>extractor</strong> aísla las
        afirmaciones, un <strong>traductor</strong> normaliza el idioma y la
        terminología clínica, y un <strong>experto en salud</strong> contrasta
        cada afirmación con fuentes como OMS, Cochrane y NIH antes de calcular
        la puntuación.
      </>
    ),
    plain:
      'Tres agentes de IA trabajan en cadena: un extractor aísla las afirmaciones, un traductor normaliza el idioma y la terminología clínica, y un experto en salud contrasta cada afirmación con fuentes como OMS, Cochrane y NIH.',
    open: false,
  },
  {
    q: '¿Qué formatos de contenido puedo analizar?',
    a: (
      <>
        Puedes pegar <strong>texto</strong>, introducir un{' '}
        <strong>enlace</strong> (URL de un artículo) o subir un{' '}
        <strong>archivo</strong>: PDF, DOCX, TXT e imágenes (PNG y JPG).
      </>
    ),
    plain:
      'Texto pegado, enlaces (URL de artículos) y archivos: PDF, DOCX, TXT e imágenes (PNG y JPG).',
    open: false,
  },
  {
    q: '¿Cuál es la precisión de la herramienta?',
    a: (
      <>
        VeriTrust alcanza un <strong>88% de precisión</strong>, medido sobre más
        de 10.000 análisis verificados. Cada veredicto incluye sus fuentes para
        que puedas comprobarlo por ti mismo.
      </>
    ),
    plain:
      'VeriTrust alcanza un 88% de precisión medido sobre más de 10.000 análisis verificados.',
    open: false,
  },
  {
    q: '¿Mis datos y los de mi organización están seguros?',
    a: (
      <>
        Sí. El contenido se procesa de forma privada y{' '}
        <strong>no se utiliza para entrenar modelos</strong>. Para instituciones
        ofrecemos acuerdos de tratamiento de datos y opciones de despliegue
        dedicado.
      </>
    ),
    plain:
      'El contenido se procesa de forma privada y no se utiliza para entrenar modelos. Ofrecemos acuerdos de tratamiento de datos para instituciones.',
    open: false,
  },
  {
    q: '¿Hay una versión gratuita?',
    a: (
      <>
        Sí. El plan <strong>Gratis</strong> incluye 10 análisis al mes con los
        tres agentes y las tres vías de entrada, sin necesidad de tarjeta.
      </>
    ),
    plain:
      'Sí. El plan Gratis incluye 10 análisis al mes con los tres agentes y los tres tipos de entrada.',
    open: false,
  },
];

export default function Faq() {
  return (
    <section id="faq" className="bg-[#eeedf8] py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Preguntas frecuentes
          </span>
          <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
            Todo sobre el detector de noticias falsas de salud
          </h2>
        </div>
        <div className="mx-auto flex max-w-195 flex-col gap-3.5">
          {faqEntries.map(item => (
            <details
              key={item.q}
              open={item.open}
              className="group overflow-hidden rounded-2xl border border-[#e8e6f4] bg-white shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]"
            >
              <summary className="flex cursor-pointer list-none items-center gap-4 px-6 py-5.5 text-[17px] font-semibold text-[#15162c] [&::-webkit-details-marker]:hidden">
                <span className="flex-1">{item.q}</span>
                <span className="grid size-6 shrink-0 place-items-center rounded-[7px] bg-[#f4f2fd] text-primary transition group-open:rotate-45 group-open:bg-primary group-open:text-white">
                  <PlusIcon className="size-3.5" />
                </span>
              </summary>
              <div className="px-6 pb-6 text-[14.5px] leading-relaxed text-[#6f7090] [&_strong]:font-bold [&_strong]:text-[#33344c]">
                {item.a}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
