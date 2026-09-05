'use client';

import { useState } from 'react';

import PlusIcon from '@/assets/Plus';

interface FaqItem {
  cat: string;
  q: string;
  a: string;
}

export default function HelpFaq({ items }: { items: FaqItem[] }) {
  const [open, setOpen] = useState<number>(0);

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm">
      {items.map((f, i) => {
        const isOpen = open === i;
        return (
          <div key={f.q} className={`border-t border-line first:border-t-0`}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? -1 : i)}
              aria-expanded={isOpen}
              className="flex w-full items-center gap-3.5 px-5.5 py-4.5 text-left transition-colors hover:bg-surface-subtle"
            >
              <span className="flex-1 text-base leading-snug font-semibold text-ink">
                {f.q}
              </span>
              <span className="shrink-0 rounded-lg border border-line bg-surface px-2.5 py-1 text-2xs font-bold tracking-[0.04em] text-muted uppercase">
                {f.cat}
              </span>
              <span
                className={`grid size-6.5 shrink-0 place-items-center rounded-lg transition-transform ${
                  isOpen
                    ? 'rotate-45 bg-primary text-white'
                    : 'bg-surface text-accent'
                }`}
              >
                <PlusIcon width={13} height={13} strokeWidth={2.5} />
              </span>
            </button>
            <div
              className={`overflow-hidden transition-all duration-250 ${
                isOpen ? 'max-h-72' : 'max-h-0'
              }`}
            >
              <div
                className="px-5.5 pb-5 pl-15.5 text-sm leading-relaxed text-muted [&_b]:font-bold [&_b]:text-body"
                dangerouslySetInnerHTML={{ __html: f.a }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
