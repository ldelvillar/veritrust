import Arrow from '@/assets/Arrow';
import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'VeriTrust | Detector de noticias falsas de salud con IA',
  description:
    'VeriTrust es un detector de noticias falsas de salud impulsado por un sistema multiagente de IA. Verifica textos, enlaces y documentos médicos afirmación por afirmación, con un 88% de precisión y fuentes citadas (OMS, Cochrane, NIH).',
  keywords: [
    'detector de noticias falsas de salud',
    'verificar bulos médicos',
    'fact-checking médico',
    'desinformación sanitaria',
    'IA verificación salud',
    'comprobar noticias médicas',
  ],
  openGraph: {
    type: 'website',
    siteName: 'VeriTrust',
    locale: 'es_ES',
    title: 'Detector de noticias falsas de salud con IA · VeriTrust',
    description:
      'Verifica afirmaciones médicas en segundos. Tres agentes de IA analizan texto, enlaces y documentos y devuelven una puntuación de credibilidad explicada.',
  },
};

const faqEntries = [
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
        de 15.000 análisis verificados. Cada veredicto incluye sus fuentes para
        que puedas comprobarlo por ti mismo.
      </>
    ),
    plain:
      'VeriTrust alcanza un 88% de precisión medido sobre más de 15.000 análisis verificados.',
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

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'SoftwareApplication',
      name: 'VeriTrust',
      applicationCategory: 'HealthApplication',
      operatingSystem: 'Web',
      description:
        'Detector de noticias falsas de salud con un sistema multiagente de IA que verifica textos, enlaces y documentos médicos afirmación por afirmación.',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' },
    },
    {
      '@type': 'FAQPage',
      mainEntity: faqEntries.map(({ q, plain }) => ({
        '@type': 'Question',
        name: q,
        acceptedAnswer: { '@type': 'Answer', text: plain },
      })),
    },
  ],
};

const container = 'mx-auto w-full max-w-295 px-5 md:px-8';

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3.5 12h17M12 3c2.4 2.4 2.4 15.6 0 18M12 3c-2.4 2.4-2.4 15.6 0 18" />
    </svg>
  );
}

export default function Home() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ===================== HERO ===================== */}
      <section className="relative overflow-hidden bg-[linear-gradient(165deg,#5a44e8_0%,#432dd7_48%,#3722b8_100%)] py-18.5 pb-24 text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.07)_1px,transparent_1px)] bg-[length:26px_26px] opacity-60" />
        <div className="pointer-events-none absolute -top-40 -right-40 size-130 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
        <div
          className={`${container} relative z-[2] grid items-center gap-14 md:grid-cols-[1.05fr_0.95fr]`}
        >
          <div>
            <h1 className="mt-5 mb-5 text-[34px] leading-[1.12] font-bold tracking-[-0.03em] text-white sm:text-[42px] md:text-[54px]">
              El detector de noticias falsas de salud{' '}
              <span className="bg-[linear-gradient(120deg,#c9ffea,#9be8ff)] bg-clip-text text-transparent">
                impulsado por IA
              </span>
            </h1>
            <p className="max-w-140 text-[18.5px] leading-relaxed font-medium text-white/90">
              Pega un texto, un enlace o sube un documento. Tres agentes de
              inteligencia artificial verifican cada afirmación médica y te
              devuelven una puntuación de credibilidad explicada, con sus
              fuentes.
            </p>
            <div className="mt-9 mb-6 flex flex-wrap gap-3.5">
              <Link
                href="/demo"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-4 text-base font-semibold text-primary shadow-[0_8px_22px_rgba(20,22,44,0.12)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(20,22,44,0.18)]"
              >
                Solicitar demo
              </Link>
              <Link
                href="/app/analisis"
                className="inline-flex items-center justify-center gap-2 rounded-xl border-[1.5px] border-white/40 px-7 py-4 text-base font-semibold text-white transition hover:border-white hover:bg-white/10"
              >
                Analizar gratis <Arrow className="size-4 rotate-270" />
              </Link>
            </div>
            <div className="flex flex-wrap items-center gap-x-5.5 gap-y-3">
              {[
                { label: '88% de precisión' },
                { label: '+15.000 análisis' },
                { label: 'Fuentes citadas' },
              ].map((item, i) => (
                <div key={item.label} className="flex items-center gap-x-5.5">
                  {i > 0 && <span className="h-5.5 w-px bg-white/20" />}
                  <span className="flex items-center gap-2 text-sm font-semibold text-white/85">
                    <CheckIcon className="size-4.5 shrink-0 text-[#9be8ff]" />
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* product mockup */}
          <div className="relative">
            <div className="animate-floaty absolute -top-6 -left-7 z-[3] flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(60,50,140,0.18)]">
              <span className="grid size-8.5 place-items-center rounded-[9px] bg-[#def4ea] text-[#0e8e5b]">
                <CheckIcon className="size-4.5" />
              </span>
              <span className="leading-tight">
                <b className="block font-bold text-[#15162c]">4 afirmaciones</b>
                <small className="text-[11px] text-[#6f7090]">
                  verificadas por agente
                </small>
              </span>
            </div>
            <div className="animate-floaty absolute -right-6 -bottom-5 z-[3] flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(60,50,140,0.18)] [animation-delay:0.5s]">
              <span className="grid size-8.5 place-items-center rounded-[9px] bg-[#efedfc] text-primary">
                <GlobeIcon className="size-4.5" />
              </span>
              <span className="leading-tight">
                <b className="block font-bold text-[#15162c]">OMS · Cochrane</b>
                <small className="text-[11px] text-[#6f7090]">
                  fuentes consultadas
                </small>
              </span>
            </div>

            <div className="[transform:rotate(0.6deg)] overflow-hidden rounded-[20px] bg-white text-[#33344c] shadow-[0_24px_60px_rgba(60,50,140,0.18)]">
              <div className="flex items-center gap-1.75 border-b border-[#e8e6f4] bg-[#faf9fe] px-4 py-3.5">
                <i className="size-2.75 rounded-full bg-[#f0a8b4]" />
                <i className="size-2.75 rounded-full bg-[#f3d49a]" />
                <i className="size-2.75 rounded-full bg-[#a8e0c4]" />
                <span className="ml-2.5 font-mono text-[11.5px] text-[#9698b1]">
                  veriTrust.health/analizar
                </span>
              </div>
              <div className="p-5.5">
                <div className="flex items-center gap-4">
                  <div className="flex size-24 shrink-0 flex-col items-center justify-center rounded-[18px] bg-[linear-gradient(150deg,#e2607a,#d23c5d)] text-white shadow-[0_10px_22px_rgba(210,60,93,0.3)]">
                    <b className="text-[30px] leading-none font-bold">41</b>
                    <small className="mt-0.5 text-[10px] tracking-wide opacity-85">
                      / 100
                    </small>
                  </div>
                  <div>
                    <span className="text-[11px] font-extrabold tracking-[0.08em] text-[#c23552] uppercase">
                      Engañoso
                    </span>
                    <h4 className="my-1.5 text-lg font-semibold text-[#15162c]">
                      Credibilidad baja
                    </h4>
                    <p className="text-[12.5px] leading-snug text-[#6f7090]">
                      Mezcla datos ciertos con una conclusión que la evidencia
                      no respalda.
                    </p>
                  </div>
                </div>
                <div className="mt-4.5 flex flex-col gap-2.25">
                  {[
                    {
                      tone: 'ok' as const,
                      text: 'La vitamina C es esencial para el sistema inmunitario.',
                    },
                    {
                      tone: 'bad' as const,
                      text: 'Su consumo diario previene por completo el resfriado.',
                    },
                    {
                      tone: 'warn' as const,
                      text: 'Las dosis altas son «sin ningún riesgo».',
                    },
                  ].map(claim => (
                    <div
                      key={claim.text}
                      className="flex items-start gap-2.5 rounded-[11px] border border-[#e8e6f4] bg-[#faf9fe] px-3.25 py-2.75"
                    >
                      <span
                        className={`mt-px grid size-5.5 shrink-0 place-items-center rounded-md ${
                          claim.tone === 'ok'
                            ? 'bg-[#def4ea] text-[#0e8e5b]'
                            : claim.tone === 'bad'
                              ? 'bg-[#fbe4e8] text-[#c23552]'
                              : 'bg-[#fbefda] text-[#b07a16]'
                        }`}
                      >
                        {claim.tone === 'ok' ? (
                          <CheckIcon className="size-3.25 [stroke-width:2.6]" />
                        ) : claim.tone === 'bad' ? (
                          <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2.6}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="size-3.25"
                          >
                            <path d="M6 6l12 12M18 6 6 18" />
                          </svg>
                        ) : (
                          <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={2.2}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className="size-3.25"
                          >
                            <path d="M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
                          </svg>
                        )}
                      </span>
                      <span className="text-[12.5px] leading-snug font-semibold text-[#33344c]">
                        {claim.text}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex gap-1.75">
                  {[
                    { c: '#6356e6', label: 'Extractor' },
                    { c: '#2c97e8', label: 'Traductor' },
                    { c: '#13b877', label: 'Experto' },
                  ].map(a => (
                    <span
                      key={a.label}
                      className="flex flex-1 items-center gap-1.75 rounded-[9px] bg-[#f4f2fd] px-2.25 py-2 text-[10.5px] font-bold text-[#33344c]"
                    >
                      <span
                        className="size-1.75 rounded-full"
                        style={{ background: a.c }}
                      />
                      {a.label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===================== SOURCES ===================== */}
      <section
        aria-label="Fuentes médicas"
        className="border-b border-[#e8e6f4] bg-white py-9.5"
      >
        <div className={container}>
          <p className="mb-6 text-center text-[13px] font-bold tracking-[0.08em] text-[#9698b1] uppercase">
            Contrastado con fuentes médicas de referencia
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-5">
            {[
              'OMS',
              'Cochrane',
              'NIH',
              'PubMed',
              'AEMPS',
              'Ministerio de Sanidad',
            ].map(s => (
              <span
                key={s}
                className="text-[21px] font-bold tracking-tight text-[#aaabc2] grayscale transition hover:text-[#33344c] hover:grayscale-0"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== STATS ===================== */}
      <section
        aria-label="Resultados"
        className="bg-[#eeedf8] py-24 max-md:py-18"
      >
        <div className={container}>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                n: '88%',
                l: 'de precisión sobre más de 15.000 análisis verificados',
              },
              {
                n: '3',
                l: 'agentes de IA especializados trabajando en cadena',
              },
              { n: '~6 s', l: 'por análisis medio, de la entrada al informe' },
              { n: '3', l: 'vías de entrada: texto, enlace y documento' },
            ].map(stat => (
              <div
                key={stat.l}
                className="rounded-[18px] border border-[#e8e6f4] bg-white px-6.5 py-7.5 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]"
              >
                <b className="block text-[42px] leading-none font-bold tracking-[-0.03em] text-primary">
                  {stat.n}
                </b>
                <div className="mt-2.5 text-[14.5px] leading-snug font-semibold text-[#6f7090]">
                  {stat.l}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== HOW IT WORKS ===================== */}
      <section id="como-funciona" className="py-24 max-md:py-18">
        <div className={container}>
          <div className="mx-auto mb-14 max-w-170 text-center">
            <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
              Cómo funciona
            </span>
            <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
              Tres agentes, un veredicto fiable
            </h2>
            <p className="text-[17px] leading-relaxed text-[#6f7090]">
              VeriTrust no es una caja negra. Cada afirmación pasa por tres
              especialistas de IA que se complementan, y verás exactamente qué
              aportó cada uno.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                n: '01',
                bg: '#eeebfc',
                fg: '#6356e6',
                title: 'Extractor de información',
                body: 'Lee el contenido y aísla cada afirmación médica, las cifras y las fuentes citadas, sin perder el contexto.',
                chips: ['Afirmaciones', 'Cifras', 'Referencias'],
                icon: (
                  <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16M7.5 12h9" />
                ),
              },
              {
                n: '02',
                bg: '#e4f1fc',
                fg: '#2c97e8',
                title: 'Traductor',
                body: 'Normaliza el idioma y estandariza la terminología clínica para que cada afirmación se contraste sobre una base común.',
                chips: ['Idioma', 'Terminología', 'Normalización'],
                icon: (
                  <>
                    <circle cx="12" cy="12" r="9" />
                    <path d="M3.5 9h17M3.5 15h17M12 3c2.4 2.4 2.4 15.6 0 18M12 3c-2.4 2.4-2.4 15.6 0 18" />
                  </>
                ),
              },
              {
                n: '03',
                bg: '#def4ea',
                fg: '#13b877',
                title: 'Experto en salud',
                body: 'Contrasta cada afirmación con el consenso médico y las fuentes de referencia, y calcula la puntuación de credibilidad.',
                chips: ['Consenso', 'Fuentes', 'Puntuación'],
                icon: <path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" />,
              },
            ].map(step => (
              <article
                key={step.n}
                className="relative rounded-[20px] border border-[#e8e6f4] bg-white px-7 py-7.5 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)]"
              >
                <span className="absolute top-6 right-6.5 text-[15px] font-bold text-[#9698b1]">
                  {step.n}
                </span>
                <div
                  className="mb-5 grid size-14 place-items-center rounded-[15px]"
                  style={{ background: step.bg, color: step.fg }}
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.9}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="size-6.75"
                  >
                    {step.icon}
                  </svg>
                </div>
                <h3 className="mb-2.5 text-xl font-semibold text-[#15162c]">
                  {step.title}
                </h3>
                <p className="text-[14.5px] leading-relaxed text-[#6f7090]">
                  {step.body}
                </p>
                <div className="mt-4 flex flex-wrap gap-1.75">
                  {step.chips.map(chip => (
                    <span
                      key={chip}
                      className="rounded-[7px] border border-[#e8e6f4] bg-[#faf9fe] px-2.5 py-1.25 text-[11.5px] font-bold text-[#33344c]"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== FEATURES ===================== */}
      <section id="features" className="bg-[#eeedf8] py-24 max-md:py-18">
        <div className={container}>
          <div className="mx-auto mb-14 max-w-170 text-center">
            <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
              Características
            </span>
            <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
              Todo lo que necesitas para verificar con rigor
            </h2>
            <p className="text-[17px] leading-relaxed text-[#6f7090]">
              Pensado para equipos que no pueden permitirse publicar o difundir
              un bulo médico.
            </p>
          </div>
          <div className="grid gap-5.5 md:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: 'Tres vías de entrada',
                body: 'Analiza texto pegado, enlaces de artículos o documentos (PDF, DOCX, TXT e imágenes) desde una sola herramienta.',
                icon: <path d="M4 7V5h16v2M9 19h6M12 5v14" />,
              },
              {
                title: 'Análisis afirmación por afirmación',
                body: 'No una etiqueta genérica: cada frase verificable recibe su propio veredicto, con explicación y matices.',
                icon: (
                  <>
                    <line x1="8" y1="6" x2="20" y2="6" />
                    <line x1="8" y1="12" x2="20" y2="12" />
                    <line x1="8" y1="18" x2="20" y2="18" />
                    <circle cx="3.5" cy="6" r="1" />
                    <circle cx="3.5" cy="12" r="1" />
                    <circle cx="3.5" cy="18" r="1" />
                  </>
                ),
              },
              {
                title: 'Fuentes médicas citadas',
                body: 'Cada veredicto enlaza las referencias usadas —OMS, Cochrane, NIH— para que puedas auditarlo y defenderlo.',
                icon: (
                  <>
                    <circle cx="12" cy="12" r="9" />
                    <path d="M3.5 12h17M12 3c2.4 2.4 2.4 15.6 0 18M12 3c-2.4 2.4-2.4 15.6 0 18" />
                  </>
                ),
              },
              {
                title: 'Informes exportables',
                body: 'Descarga el informe completo en PDF para tu fact-check, tu campaña o tu archivo editorial.',
                icon: (
                  <path d="M12 16V4M7 9l5-5 5 5M5 18v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1" />
                ),
              },
              {
                title: 'API e integración',
                body: 'Conecta VeriTrust a tu CMS o a tu flujo de monitorización para verificar a escala, sin trabajo manual.',
                icon: <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />,
              },
              {
                title: 'Privacidad por diseño',
                body: 'El contenido se procesa de forma privada y no se usa para entrenar modelos. Acuerdos de datos para instituciones.',
                icon: (
                  <>
                    <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z" />
                    <path d="M9 12l2 2 4-4" />
                  </>
                ),
              },
            ].map(feat => (
              <article
                key={feat.title}
                className="rounded-[18px] border border-[#e8e6f4] bg-white p-6.5 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)] transition hover:-translate-y-0.75 hover:shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)]"
              >
                <div className="mb-4 grid size-11.5 place-items-center rounded-xl bg-[#efedfc] text-primary">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.9}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="size-5.5"
                  >
                    {feat.icon}
                  </svg>
                </div>
                <h3 className="mb-2 text-[17px] font-semibold text-[#15162c]">
                  {feat.title}
                </h3>
                <p className="text-sm leading-relaxed text-[#6f7090]">
                  {feat.body}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== SAMPLE REPORT ===================== */}
      <section id="ejemplo" className="py-24 max-md:py-18">
        <div
          className={`${container} grid items-center gap-12 md:grid-cols-[0.9fr_1.1fr]`}
        >
          <div>
            <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
              Un informe real
            </span>
            <h2 className="my-4 text-[28px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[36px]">
              Mira cómo VeriTrust desmonta un bulo
            </h2>
            <p className="mb-5 text-base leading-relaxed text-[#6f7090]">
              Analizamos una afirmación habitual: «la vitamina C en dosis altas
              previene por completo el resfriado». Esto es lo que devuelve el
              sistema.
            </p>
            <div className="mt-6 flex flex-col gap-3.5">
              {[
                {
                  b: 'Puntuación explicada',
                  p: '41/100 · «Engañoso»: mezcla un hecho real con una conclusión sin respaldo.',
                },
                {
                  b: 'Cada afirmación, por separado',
                  p: 'Verificado, falso, impreciso o sin fuente: cuatro veredictos distintos en un mismo texto.',
                },
                {
                  b: 'Fuentes para defenderlo',
                  p: 'Las revisiones de Cochrane y las fichas del NIH respaldan el veredicto.',
                },
              ].map(li => (
                <div key={li.b} className="flex items-start gap-3.25">
                  <span className="grid size-7.5 shrink-0 place-items-center rounded-[9px] bg-[#def4ea] text-[#0e8e5b]">
                    <CheckIcon className="size-4" />
                  </span>
                  <div>
                    <b className="font-semibold text-[#15162c]">{li.b}</b>
                    <p className="mt-0.75 text-[13.5px] text-[#6f7090]">
                      {li.p}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-7.5">
              <Link
                href="/app/analisis"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-7 py-4 text-base font-semibold text-white shadow-[0_8px_22px_rgba(67,45,215,0.32)] transition hover:-translate-y-0.5 hover:bg-[#3722b8] hover:shadow-[0_14px_30px_rgba(67,45,215,0.42)]"
              >
                Probar con tu propio texto{' '}
                <Arrow className="size-4 rotate-270" />
              </Link>
            </div>
          </div>

          <div className="overflow-hidden rounded-[22px] border border-[#e8e6f4] bg-white shadow-[0_24px_60px_rgba(60,50,140,0.18)]">
            <div className="flex items-center gap-1.75 border-b border-[#e8e6f4] bg-[#faf9fe] px-4.5 py-3.5">
              <i className="size-2.75 rounded-full bg-[#f0a8b4]" />
              <i className="size-2.75 rounded-full bg-[#f3d49a]" />
              <i className="size-2.75 rounded-full bg-[#a8e0c4]" />
              <span className="ml-3 rounded-[7px] bg-[#efedfc] px-3 py-1.25 text-xs font-bold text-primary">
                Informe de credibilidad
              </span>
            </div>
            <div className="p-6">
              <div className="mb-5 flex items-center gap-4.5">
                <div className="flex size-30 shrink-0 flex-col items-center justify-center rounded-[20px] bg-[linear-gradient(150deg,#e2607a,#d23c5d)] text-white shadow-[0_12px_26px_rgba(210,60,93,0.3)]">
                  <b className="text-[40px] leading-none font-bold">41</b>
                  <small className="text-[11px] opacity-85">/ 100</small>
                </div>
                <div>
                  <span className="text-[11px] font-extrabold tracking-[0.06em] text-[#c23552] uppercase">
                    Engañoso
                  </span>
                  <h4 className="my-1.5 text-[21px] font-semibold text-[#15162c]">
                    Credibilidad baja
                  </h4>
                  <p className="text-[13px] leading-snug text-[#6f7090]">
                    Parte de un hecho real pero exagera sus efectos y contradice
                    el consenso clínico.
                  </p>
                </div>
              </div>
              <div className="mt-1.5 mb-3 text-xs font-extrabold tracking-[0.06em] text-[#9698b1] uppercase">
                Afirmaciones detectadas
              </div>
              {[
                {
                  tone: 'ok' as const,
                  text: 'La vitamina C es un nutriente esencial para el sistema inmunitario.',
                  verdict: 'Verificado',
                },
                {
                  tone: 'bad' as const,
                  text: 'Su consumo diario previene por completo el resfriado común.',
                  verdict: 'Falso',
                },
                {
                  tone: 'warn' as const,
                  text: 'Refuerza el sistema inmunitario «sin ningún riesgo».',
                  verdict: 'Impreciso',
                },
              ].map((claim, idx) => (
                <div
                  key={claim.text}
                  className={`flex gap-3 py-3.25 ${idx > 0 ? 'border-t border-[#e8e6f4]' : ''}`}
                >
                  <span
                    className={`mt-px grid size-6 shrink-0 place-items-center rounded-[7px] ${
                      claim.tone === 'ok'
                        ? 'bg-[#def4ea] text-[#0e8e5b]'
                        : claim.tone === 'bad'
                          ? 'bg-[#fbe4e8] text-[#c23552]'
                          : 'bg-[#fbefda] text-[#b07a16]'
                    }`}
                  >
                    {claim.tone === 'ok' ? (
                      <CheckIcon className="size-3.25 [stroke-width:2.6]" />
                    ) : claim.tone === 'bad' ? (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2.6}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="size-3.25"
                      >
                        <path d="M6 6l12 12M18 6 6 18" />
                      </svg>
                    ) : (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2.2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="size-3.25"
                      >
                        <path d="M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
                      </svg>
                    )}
                  </span>
                  <div>
                    <div className="text-[13.5px] leading-snug font-semibold text-[#33344c]">
                      {claim.text}
                    </div>
                    <span
                      className={`mt-1 inline-block text-[10.5px] font-extrabold tracking-[0.04em] uppercase ${
                        claim.tone === 'ok'
                          ? 'text-[#0e8e5b]'
                          : claim.tone === 'bad'
                            ? 'text-[#c23552]'
                            : 'text-[#b07a16]'
                      }`}
                    >
                      {claim.verdict}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===================== USE CASES ===================== */}
      <section
        id="casos"
        className="bg-[#16172e] py-24 text-white max-md:py-18"
      >
        <div className={container}>
          <div className="mx-auto mb-14 max-w-170 text-center">
            <span className="text-[13px] font-extrabold tracking-[0.12em] text-[#bdb3ff] uppercase">
              Casos de uso
            </span>
            <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-white md:text-[40px]">
              Hecho para quienes combaten la desinformación
            </h2>
            <p className="text-[17px] leading-relaxed text-white/70">
              Desde redacciones hasta organismos de salud pública, VeriTrust
              acelera la verificación sin renunciar al rigor.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            {[
              {
                title: 'Periodistas y verificadores',
                body: 'Comprueba afirmaciones de salud antes de publicar y obtén un informe con fuentes citadas que respalda tu fact-check.',
                items: [
                  'Verificación en segundos, no en horas',
                  'Informe exportable como evidencia',
                  'Historial de todo lo analizado',
                ],
                icon: (
                  <path d="M4 4h12a2 2 0 0 1 2 2v13a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2zM18 8h2a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2M7 8h7M7 12h7M7 16h4" />
                ),
              },
              {
                title: 'Salud pública e instituciones',
                body: 'Monitoriza y desmiente bulos sanitarios a escala. Integra VeriTrust por API y exporta informes para tus campañas.',
                items: [
                  'API para verificar a gran volumen',
                  'Usuarios en equipo y SSO',
                  'Acuerdos de tratamiento de datos',
                ],
                icon: <path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-6h6v6" />,
              },
            ].map(uc => (
              <article
                key={uc.title}
                className="rounded-[20px] border border-white/10 bg-white/5 p-8.5 transition hover:border-white/20 hover:bg-white/[0.08]"
              >
                <div className="mb-5 grid size-12.5 place-items-center rounded-[13px] bg-[rgba(124,110,240,0.22)] text-[#bdb3ff]">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.9}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="size-6"
                  >
                    {uc.icon}
                  </svg>
                </div>
                <h3 className="mb-3 text-[22px] font-semibold text-white">
                  {uc.title}
                </h3>
                <p className="mb-4.5 text-[14.5px] leading-relaxed text-white/70">
                  {uc.body}
                </p>
                <ul className="flex flex-col gap-2.5">
                  {uc.items.map(item => (
                    <li
                      key={item}
                      className="flex items-center gap-2.5 text-sm font-medium text-white/85"
                    >
                      <CheckIcon className="size-4.25 shrink-0 text-[#8effc8]" />
                      {item}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== PRICING ===================== */}
      <section id="precios" className="py-24 max-md:py-18">
        <div className={container}>
          <div className="mx-auto mb-14 max-w-170 text-center">
            <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
              Precios
            </span>
            <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
              Empieza gratis, crece cuando lo necesites
            </h2>
            <p className="text-[17px] leading-relaxed text-[#6f7090]">
              Sin tarjeta para probar. Cambia o cancela tu plan cuando quieras.
            </p>
          </div>
          <div className="grid items-stretch gap-6 md:grid-cols-3">
            {[
              {
                name: 'Gratis',
                desc: 'Para curiosos y primeras verificaciones.',
                price: '0€',
                unit: '/ mes',
                items: [
                  '10 análisis al mes',
                  'Los 3 agentes de IA',
                  'Texto, enlace y archivo',
                  'Informe con fuentes',
                ],
                cta: {
                  label: 'Analizar gratis',
                  href: '/app/analisis',
                  soft: true,
                },
                featured: false,
              },
              {
                name: 'Pro',
                desc: 'Para periodistas y verificadores profesionales.',
                price: '29€',
                unit: '/ mes',
                items: [
                  '500 análisis al mes',
                  'Historial y panel completos',
                  'Exportar informes en PDF',
                  'API básica y prioridad',
                ],
                cta: {
                  label: 'Empezar con Pro',
                  href: '/demo',
                  soft: false,
                },
                featured: true,
              },
              {
                name: 'Clínica',
                desc: 'Para organizaciones de salud pública e instituciones.',
                price: 'A medida',
                unit: '',
                items: [
                  'Análisis ilimitados',
                  'Usuarios en equipo y SSO',
                  'API completa e integración',
                  'Soporte y acuerdos de datos',
                ],
                cta: { label: 'Solicitar demo', href: '/demo', soft: true },
                featured: false,
              },
            ].map(plan => (
              <article
                key={plan.name}
                className={`relative flex flex-col rounded-[22px] bg-white px-7.5 py-8.5 ${
                  plan.featured
                    ? 'border-2 border-primary shadow-[0_24px_60px_rgba(60,50,140,0.18)]'
                    : 'border border-[#e8e6f4] shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]'
                }`}
              >
                {plan.featured && (
                  <span className="absolute -top-3.25 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3.5 py-1.5 text-[11.5px] font-extrabold tracking-[0.05em] text-white uppercase">
                    Más popular
                  </span>
                )}
                <div className="text-[19px] font-bold text-[#15162c]">
                  {plan.name}
                </div>
                <p className="mt-1.5 mb-5.5 min-h-10 text-[13.5px] leading-snug text-[#6f7090]">
                  {plan.desc}
                </p>
                <div className="mb-5.5 flex items-baseline gap-1.5">
                  <b className="text-[44px] font-bold tracking-[-0.03em] text-[#15162c]">
                    {plan.price}
                  </b>
                  {plan.unit && (
                    <span className="text-[15px] font-semibold text-[#6f7090]">
                      {plan.unit}
                    </span>
                  )}
                </div>
                <ul className="mb-6.5 flex flex-1 flex-col gap-3.25">
                  {plan.items.map(item => (
                    <li
                      key={item}
                      className="flex items-start gap-2.5 text-sm font-medium text-[#33344c]"
                    >
                      <CheckIcon className="mt-0.5 size-4.25 shrink-0 text-[#13b877]" />
                      {item}
                    </li>
                  ))}
                </ul>
                {plan.cta.href.startsWith('/') ? (
                  <Link
                    href={plan.cta.href}
                    className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-5.5 py-3.25 text-[15px] font-semibold transition ${
                      plan.cta.soft
                        ? 'border border-[#dcd9ee] bg-white text-[#33344c] hover:border-primary hover:text-primary'
                        : 'bg-primary text-white shadow-[0_8px_22px_rgba(67,45,215,0.32)] hover:bg-[#3722b8]'
                    }`}
                  >
                    {plan.cta.label}
                  </Link>
                ) : (
                  <a
                    href={plan.cta.href}
                    className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-5.5 py-3.25 text-[15px] font-semibold transition ${
                      plan.cta.soft
                        ? 'border border-[#dcd9ee] bg-white text-[#33344c] hover:border-primary hover:text-primary'
                        : 'bg-primary text-white shadow-[0_8px_22px_rgba(67,45,215,0.32)] hover:bg-[#3722b8]'
                    }`}
                  >
                    {plan.cta.label}
                  </a>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== FAQ ===================== */}
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
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2.4}
                      strokeLinecap="round"
                      className="size-3.5"
                    >
                      <path d="M12 5v14M5 12h14" />
                    </svg>
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

      {/* ===================== CTA ===================== */}
      <section id="contacto" className="bg-white py-20">
        <div className={container}>
          <div className="relative overflow-hidden rounded-[28px] bg-[linear-gradient(150deg,#5a44e8,#432dd7_55%,#3722b8)] px-14 py-16 text-center text-white max-md:px-6 max-md:py-12">
            <div className="pointer-events-none absolute -top-30 -right-25 size-95 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
            <div className="relative z-[2] mx-auto max-w-160">
              <span className="inline-flex items-center gap-2.5 rounded-full border border-white/20 bg-white/15 px-3.5 py-2 text-[12.5px] font-extrabold tracking-[0.1em] whitespace-nowrap text-white uppercase">
                <span className="size-1.75 animate-pulse rounded-full bg-[#13b877] shadow-[0_0_0_4px_rgba(19,184,119,0.25)]" />
                Empieza hoy
              </span>
              <h2 className="mt-4.5 mb-4 text-[30px] font-bold tracking-[-0.02em] text-white md:text-[40px]">
                Frena la desinformación médica antes de que se difunda
              </h2>
              <p className="mb-8 text-lg leading-snug text-white/90">
                Solicita una demo para tu redacción o tu institución, o empieza
                a analizar gratis ahora mismo.
              </p>
              <div className="flex flex-wrap justify-center gap-3.5">
                <Link
                  href="/demo"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-4 text-base font-semibold text-primary shadow-[0_8px_22px_rgba(20,22,44,0.12)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(20,22,44,0.18)]"
                >
                  Solicitar demo
                </Link>
                <Link
                  href="/app/analisis"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border-[1.5px] border-white/40 px-7 py-4 text-base font-semibold text-white transition hover:border-white hover:bg-white/10"
                >
                  Analizar gratis <Arrow className="size-4 rotate-270" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
