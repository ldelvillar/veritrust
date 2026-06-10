import BookIcon from '@/assets/Book';
import ShieldIcon from '@/assets/Shield';
import SourceRow from './SourceRow';
import type { SourceType } from './types';

export default function SourcesCard({
  sources,
  title,
  caption,
}: {
  sources: SourceType[];
  title: string;
  caption: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <BookIcon className="size-4.5 text-primary" />
        {title}
      </h3>
      <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
        {caption}
      </p>

      <ul>
        {sources.map((source, index) => (
          <SourceRow key={`${source.url}-${index}`} source={source} />
        ))}
      </ul>

      <p className="mt-4 flex items-center gap-2 text-xs leading-relaxed text-slate-400">
        <ShieldIcon className="size-3.5 shrink-0" />
        Fuentes sugeridas automáticamente; verifica siempre la referencia
        original.
      </p>
    </div>
  );
}
