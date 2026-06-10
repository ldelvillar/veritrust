import WarningIcon from '@/assets/Warning';

export default function Disclaimer() {
  return (
    <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 print:break-inside-avoid">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-amber-200 bg-white text-amber-700">
        <WarningIcon className="size-4.5" />
      </div>
      <div>
        <h4 className="text-[13.5px] font-bold text-amber-800">
          Herramienta orientativa
        </h4>
        <p className="mt-0.5 text-[12.5px] leading-relaxed text-amber-700">
          Veritrust evalúa la credibilidad de la información. No emite
          diagnósticos ni sustituye la consulta con un profesional sanitario.
        </p>
      </div>
    </div>
  );
}
