import Magnifier from '@/assets/Magnifier';

export default function HistoryFilters() {
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
      <label className="relative block">
        <Magnifier className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          readOnly
          placeholder="Buscar artículos por título o palabra clave"
          className="h-11 w-full rounded-xl border border-border bg-white pl-10 text-sm text-slate-500 outline-none"
        />
      </label>

      <button
        type="button"
        className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
      >
        Todos los tipos
      </button>

      <button
        type="button"
        className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
      >
        Rango de fechas
      </button>

      <button
        type="button"
        className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
      >
        Puntuación: mayor a menor
      </button>
    </div>
  );
}
