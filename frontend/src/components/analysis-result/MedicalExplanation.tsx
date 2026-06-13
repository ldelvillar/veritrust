import { MarkdownHooks } from 'react-markdown';
import MedicalCross from '@/assets/MedicalCross';

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
        </div>
        <div className="min-w-0">
          <h3 className="flex items-center gap-2.5 text-base font-bold text-slate-900">
            Experto en salud
          </h3>
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
    </div>
  );
}
