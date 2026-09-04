import Arrow from '@/assets/Arrow';
import PublicButton from '@/components/PublicButton';
import { container } from './container';

const claims = [
  {
    n: '01',
    tone: 'ok' as const,
    text: 'La vitamina C es esencial para el sistema inmunitario.',
    verdict: 'Respaldado',
    source: 'OMS',
  },
  {
    n: '02',
    tone: 'bad' as const,
    text: 'Su consumo diario previene por completo el resfriado.',
    verdict: 'Refutado',
    source: 'Cochrane 2023',
  },
  {
    n: '03',
    tone: 'warn' as const,
    text: 'Las dosis altas son «sin ningún riesgo».',
    verdict: 'Sin consenso',
    source: 'NIH',
  },
];

const dotTone = {
  ok: 'bg-verdict-real',
  bad: 'bg-verdict-fake',
  warn: 'bg-verdict-uncertain',
};

const verdictTone = {
  ok: 'text-verdict-real-ink',
  bad: 'text-verdict-fake-ink',
  warn: 'text-verdict-uncertain-ink',
};

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
            <PublicButton href="/demo" variant="light" size="lg">
              Solicitar demo
            </PublicButton>
            <PublicButton href="/app/analisis" variant="outline" size="lg">
              Analizar gratis <Arrow className="size-4 rotate-270" />
            </PublicButton>
          </div>
        </div>

        {/* product mockup */}
        <div className="relative">
          <div
            role="img"
            aria-label="Captura del informe de credibilidad de VeriTrust mostrando una puntuación de 41 sobre 100 con veredicto Falso"
            className="transform-[rotate(0.6deg)] overflow-hidden rounded-[20px] bg-white text-body shadow-[0_24px_60px_rgba(18,33,31,0.16)]"
          >
            <div
              aria-hidden
              className="flex items-center gap-1.75 border-b border-line bg-surface-subtle px-4 py-3.5"
            >
              <i className="size-2.75 rounded-full bg-verdict-fake-soft" />
              <i className="size-2.75 rounded-full bg-verdict-uncertain-soft" />
              <i className="size-2.75 rounded-full bg-verdict-real-soft" />
              <span className="ml-2.5 font-mono text-[11.5px] text-faint">
                https://veritrust.es/analizar
              </span>
            </div>
            <div className="px-7 pt-7.5 pb-6.5">
              <div className="flex items-start justify-between gap-5">
                <div>
                  <span className="text-[11px] font-extrabold tracking-[0.08em] text-verdict-fake-ink uppercase">
                    Veredicto · Falso
                  </span>
                  <h4 className="mt-1.5 font-display text-[34px] leading-[1.06] font-normal tracking-[-0.01em] text-ink">
                    Credibilidad baja
                  </h4>
                </div>
                <div className="shrink-0 text-right">
                  <b className="block font-display text-[52px] leading-[0.85] font-normal text-verdict-fake-ink">
                    41
                  </b>
                  <small className="font-mono text-[10px] tracking-[0.08em] text-faint">
                    / 100
                  </small>
                </div>
              </div>
              <p className="mt-3 max-w-[44ch] text-[13px] leading-[1.55] text-muted">
                Mezcla datos ciertos con una conclusión que la evidencia
                científica no respalda.
              </p>
              <div className="my-5 h-px bg-line" />
              <div>
                {claims.map(claim => (
                  <div
                    key={claim.n}
                    className="grid grid-cols-[26px_1fr] gap-3 border-t border-line py-3.25 first:border-t-0"
                  >
                    <span className="pt-0.5 font-mono text-[11px] text-faint">
                      {claim.n}
                    </span>
                    <div>
                      <p className="text-[13.5px] leading-[1.4] font-medium text-ink">
                        {claim.text}
                      </p>
                      <p className="mt-1.5 flex items-center gap-2 font-mono text-[10px] tracking-[0.06em] uppercase">
                        <span
                          aria-hidden
                          className={`size-1.5 rounded-full ${dotTone[claim.tone]}`}
                        />
                        <span
                          className={`mt-1 inline-block text-[10.5px] font-extrabold tracking-[0.04em] ${verdictTone[claim.tone]}`}
                        >
                          {claim.verdict}
                        </span>
                        <span className="text-faint">{claim.source}</span>
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
