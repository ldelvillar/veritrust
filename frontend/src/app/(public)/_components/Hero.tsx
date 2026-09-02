import Arrow from '@/assets/Arrow';
import CheckIcon from '@/assets/Check';
import CrossIcon from '@/assets/Cross';
import GlobeIcon from '@/assets/Globe';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import { container } from './container';

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-primary py-18.5 pb-24 text-white">
      <div
        className={`${container} relative z-2 grid items-center gap-14 md:grid-cols-[1.05fr_0.95fr]`}
      >
        <div>
          <h1 className="mt-5 mb-5 pr-1 font-display text-[36px] leading-[1.08] font-normal tracking-[-0.01em] text-white sm:text-[44px] md:text-[56px]">
            El detector de desinformación en salud{' '}
            <em className="pr-1 italic">impulsado por IA</em>
          </h1>
          <p className="max-w-140 text-[18.5px] leading-relaxed font-normal text-white/90">
            Comprueba la veracidad de cualquier texto médico de forma rigurosa.
            Nuestro sistema analiza cada afirmación y genera un informe
            respaldado por fuentes científicas.
          </p>
          <div className="mt-9 mb-6 flex flex-wrap gap-3.5">
            <Button href="/demo" variant="light" size="lg">
              Solicitar demo
            </Button>
            <Button href="/app/analisis" variant="outline" size="lg">
              Analizar gratis <Arrow className="size-4 rotate-270" />
            </Button>
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
                  <CheckIcon className="size-4.5 shrink-0 text-white/70" />
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* product mockup */}
        <div className="relative">
          <div className="animate-floaty absolute -top-6 -left-7 z-3 flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(18,33,31,0.16)]">
            <span className="grid size-8.5 place-items-center rounded-[9px] bg-verdict-real-soft text-verdict-real-ink">
              <CheckIcon className="size-4.5" />
            </span>
            <span className="leading-tight">
              <b className="block font-bold text-ink">4 afirmaciones</b>
              <small className="text-[11px] text-muted">
                verificadas por agente
              </small>
            </span>
          </div>
          <div className="animate-floaty absolute -right-6 -bottom-5 z-3 flex items-center gap-3 rounded-[13px] bg-white px-3.75 py-3 shadow-[0_24px_60px_rgba(18,33,31,0.16)] [animation-delay:0.5s]">
            <span className="grid size-8.5 place-items-center rounded-[9px] bg-primary-soft text-primary">
              <GlobeIcon className="size-4.5" />
            </span>
            <span className="leading-tight">
              <b className="block font-bold text-ink">OMS · Cochrane</b>
              <small className="text-[11px] text-muted">
                fuentes consultadas
              </small>
            </span>
          </div>

          <div className="transform-[rotate(0.6deg)] overflow-hidden rounded-[20px] bg-white text-body shadow-[0_24px_60px_rgba(18,33,31,0.16)]">
            <div className="flex items-center gap-1.75 border-b border-line bg-surface-subtle px-4 py-3.5">
              <i className="size-2.75 rounded-full bg-verdict-fake-soft" />
              <i className="size-2.75 rounded-full bg-verdict-uncertain-soft" />
              <i className="size-2.75 rounded-full bg-verdict-real-soft" />
              <span className="ml-2.5 font-mono text-[11.5px] text-faint">
                https://veritrust.es/analizar
              </span>
            </div>
            <div className="p-5.5">
              <div className="flex items-center gap-4">
                <div className="flex size-24 shrink-0 flex-col items-center justify-center rounded-[18px] bg-[linear-gradient(150deg,var(--color-verdict-fake-g1),var(--color-verdict-fake-g2))] text-white shadow-[0_10px_22px_rgba(210,60,93,0.3)]">
                  <b className="text-[30px] leading-none font-bold">41</b>
                  <small className="mt-0.5 text-[10px] tracking-wide opacity-85">
                    / 100
                  </small>
                </div>
                <div>
                  <span className="text-[11px] font-extrabold tracking-[0.08em] text-verdict-fake-ink uppercase">
                    Falso
                  </span>
                  <h4 className="my-1.5 text-lg font-semibold text-ink">
                    Credibilidad baja
                  </h4>
                  <p className="text-[12.5px] leading-snug text-muted">
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
                    className="flex items-start gap-2.5 rounded-[11px] border border-line bg-surface-subtle px-3.25 py-2.75"
                  >
                    <span
                      className={`mt-px grid size-5.5 shrink-0 place-items-center rounded-md ${
                        claim.tone === 'ok'
                          ? 'bg-verdict-real-soft text-verdict-real-ink'
                          : claim.tone === 'bad'
                            ? 'bg-verdict-fake-soft text-verdict-fake-ink'
                            : 'bg-verdict-uncertain-soft text-verdict-uncertain-ink'
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
                    <span className="text-[12.5px] leading-snug font-semibold text-body">
                      {claim.text}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-1.75">
                {['Extractor', 'Traductor', 'Investigador', 'Experto'].map(
                  label => (
                    <span
                      key={label}
                      className="flex items-center gap-1.75 rounded-[9px] bg-surface px-2.25 py-2 text-[10.5px] font-bold text-body"
                    >
                      <span className="size-1.75 rounded-full bg-primary" />
                      {label}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
