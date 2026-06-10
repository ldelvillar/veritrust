import { MarkdownHooks } from 'react-markdown';
import MedicalCross from '@/assets/MedicalCross';
import ShieldIcon from '@/assets/Shield';

export default function MedicalExplanation({
  explanation,
}: {
  explanation: string;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-3.5 border-b border-slate-100 bg-linear-to-b from-[#faf9fe] to-white px-6 py-5">
        <div className="relative grid size-12 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-emerald-600">
          <MedicalCross className="size-6" />
          <span className="absolute -right-0.5 -bottom-0.5 size-3.5 rounded-full border-[2.5px] border-white bg-emerald-500" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 text-base font-bold text-slate-900">
            Experto en salud
            <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-bold tracking-wide text-primary uppercase">
              Agente IA
            </span>
          </div>
          <p className="mt-0.5 text-[12.5px] text-slate-500">
            Contrasta cada afirmación con el consenso médico actual
          </p>
        </div>
      </div>

      <div className="px-6 py-5">
        <div className="prose max-w-none text-slate-700 prose-slate">
          <MarkdownHooks>{explanation}</MarkdownHooks>
        </div>
      </div>

      <div className="flex items-center gap-2.5 px-6 pt-1 pb-5 text-xs leading-relaxed text-slate-400">
        <ShieldIcon className="size-3.75 shrink-0" />
        <span>
          Explicación generada por el agente médico a partir del análisis. Tiene
          carácter orientativo y no sustituye el consejo de un profesional
          sanitario.
        </span>
      </div>
    </div>
  );
}
