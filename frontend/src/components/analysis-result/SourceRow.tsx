import BookIcon from '@/assets/Book';
import type { SourceType } from './types';

function sourceMeta(source: SourceType): string | null {
  const parts = [source.source, source.year].filter((part): part is string =>
    Boolean(part)
  );
  return parts.length > 0 ? parts.join(' · ') : null;
}

export default function SourceRow({ source }: { source: SourceType }) {
  const meta = sourceMeta(source);

  return (
    <li className="flex gap-3 border-t border-slate-100 py-3.5 first:border-t-0 first:pt-0.5 print:break-inside-avoid">
      <div className="grid size-7 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
        <BookIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm leading-snug font-bold text-slate-900 underline-offset-2 hover:text-primary hover:underline focus:ring-2 focus:ring-primary/20 focus:outline-none"
        >
          {source.title}
        </a>
        {meta && (
          <p className="mt-1 text-[11.5px] font-semibold text-slate-400">
            {meta}
          </p>
        )}
      </div>
    </li>
  );
}
