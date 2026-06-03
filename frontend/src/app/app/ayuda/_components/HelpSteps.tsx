import type { HelpStep } from '../helpContent';

interface HelpStepsProps {
  steps: HelpStep[];
}

export default function HelpSteps({ steps }: HelpStepsProps) {
  return (
    <>
      <div className="mt-10 mb-2">
        <div className="mb-1 text-[11px] font-bold tracking-[0.13em] text-primary uppercase">
          Empezar
        </div>
        <h2 className="text-[20px] font-bold tracking-[-0.02em] text-[#15162c]">
          Tu primer análisis en 3 pasos
        </h2>
        <p className="mt-1 text-[13.5px] text-[#7e7f99]">
          Así trabaja el sistema multiagente con el contenido que le aportas.
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        {steps.map(step => (
          <div
            key={step.n}
            className="flex flex-col gap-3 rounded-[18px] border border-[#e8e6f4] bg-white p-5.5 shadow-sm"
          >
            <div className="grid size-8.5 place-items-center rounded-[10px] bg-[#efedfc] text-[15px] font-bold text-[#5446dc]">
              {step.n}
            </div>
            <h3 className="text-[15px] font-bold text-[#15162c]">
              {step.title}
            </h3>
            <p className="text-[13px] leading-relaxed text-[#7e7f99]">
              {step.desc}
            </p>
            <div className="mt-auto flex flex-wrap gap-1.5 pt-1">
              {step.tags.map(tag => (
                <span
                  key={tag}
                  className="rounded-[7px] border border-[#e8e6f4] bg-[#f4f2fd] px-2.5 py-1 text-[11px] font-bold text-[#33344c]"
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
