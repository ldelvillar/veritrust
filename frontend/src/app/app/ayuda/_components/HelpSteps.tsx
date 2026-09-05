import type { HelpStep } from '../helpContent';

interface HelpStepsProps {
  steps: HelpStep[];
}

export default function HelpSteps({ steps }: HelpStepsProps) {
  return (
    <>
      <div className="mt-10 mb-2">
        <div className="mb-1 text-2xs font-bold tracking-[0.13em] text-primary uppercase">
          Empezar
        </div>
        <h2 className="text-xl font-bold tracking-[-0.02em] text-ink">
          Tu primer análisis en 3 pasos
        </h2>
        <p className="mt-1 text-sm text-muted">
          Así trabaja el sistema multiagente con el contenido que le aportas.
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        {steps.map(step => (
          <div
            key={step.n}
            className="flex flex-col gap-3 rounded-2xl border border-line bg-white p-5.5 shadow-sm"
          >
            <div className="grid size-8.5 place-items-center rounded-lg bg-primary-soft text-base font-bold text-accent">
              {step.n}
            </div>
            <h3 className="text-base font-bold text-ink">{step.title}</h3>
            <p className="text-sm leading-relaxed text-muted">{step.desc}</p>
            <div className="mt-auto flex flex-wrap gap-1.5 pt-1">
              {step.tags.map(tag => (
                <span
                  key={tag}
                  className="rounded-lg border border-line bg-surface px-2.5 py-1 text-2xs font-bold text-body"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
