import Link from 'next/link';
import Arrow from '@/assets/Arrow';
import CheckIcon from '@/assets/Check';
import CrossIcon from '@/assets/Cross';
import GlobeIcon from '@/assets/Globe';
import WarningIcon from '@/assets/Warning';
import { container } from './container';

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-[linear-gradient(165deg,#5a44e8_0%,#432dd7_48%,#3722b8_100%)] py-18.5 pb-24 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.07)_1px,transparent_1px)] bg-size-[26px_26px] opacity-60" />
      <div className="pointer-events-none absolute -top-40 -right-40 size-130 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
      <div
        className={`${container} relative z-2 grid items-center gap-14 md:grid-cols-[1.05fr_0.95fr]`}
      >
        <div>
          <h1 className="mt-5 mb-5 text-[34px] leading-[1.12] font-bold tracking-[-0.03em] text-white sm:text-[42px] md:text-[54px]">
            El detector de noticias falsas de salud{' '}
            <span className="bg-[linear-gradient(120deg,#c9ffea,#9be8ff)] bg-clip-text text-transparent">
              impulsado por IA
            </span>
          </h1>
          <p className="max-w-140 text-[18.5px] leading-relaxed font-medium text-white/90">
            Pega un texto, un enlace o sube un documento. Un sistema multiagente
            de inteligencia artificial verifica cada afirmación médica y te
            devuelve una puntuación de credibilidad explicada, con sus fuentes.
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
              { label: '+10.000 análisis' },
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
          <div className="animate-floaty absolute -top-6 -left-7 z-3 flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(60,50,140,0.18)]">
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
          <div className="animate-floaty absolute -right-6 -bottom-5 z-3 flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(60,50,140,0.18)] [animation-delay:0.5s]">
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

          <div className="transform-[rotate(0.6deg)] overflow-hidden rounded-[20px] bg-white text-[#33344c] shadow-[0_24px_60px_rgba(60,50,140,0.18)]">
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
                    Mezcla datos ciertos con una conclusión que la evidencia no
                    respalda.
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
                        <CheckIcon className="size-3.25 stroke-[2.6]" />
                      ) : claim.tone === 'bad' ? (
                        <CrossIcon className="size-3.25" />
                      ) : (
                        <WarningIcon className="size-3.25" />
                      )}
                    </span>
                    <span className="text-[12.5px] leading-snug font-semibold text-[#33344c]">
                      {claim.text}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-1.75">
                {[
                  { c: '#6356e6', label: 'Extractor' },
                  { c: '#2c97e8', label: 'Traductor' },
                  { c: '#e0922e', label: 'Investigador' },
                  { c: '#13b877', label: 'Experto' },
                ].map(a => (
                  <span
                    key={a.label}
                    className="flex items-center gap-1.75 rounded-[9px] bg-[#f4f2fd] px-2.25 py-2 text-[10.5px] font-bold text-[#33344c]"
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
  );
}
