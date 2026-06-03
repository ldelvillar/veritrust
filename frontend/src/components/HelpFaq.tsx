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
    <div className="overflow-hidden rounded-[18px] border border-[#e8e6f4] bg-white shadow-sm">
      {items.map((f, i) => {
        const isOpen = open === i;
        return (
          <div
            key={f.q}
            className={`border-t border-[#e8e6f4] first:border-t-0`}
          >
            <button
              type="button"
              onClick={() => setOpen(isOpen ? -1 : i)}
              aria-expanded={isOpen}
              className="flex w-full items-center gap-3.5 px-5.5 py-4.5 text-left transition-colors hover:bg-[#faf9fe]"
            >
              <span className="flex-1 text-[15px] leading-snug font-semibold text-[#15162c]">
                {f.q}
              </span>
              <span className="shrink-0 rounded-[7px] border border-[#e8e6f4] bg-[#f4f2fd] px-2.5 py-1 text-[10.5px] font-bold tracking-[0.04em] text-[#7e7f99] uppercase">
                {f.cat}
              </span>
              <span
                className={`grid size-6.5 shrink-0 place-items-center rounded-lg transition-transform ${
                  isOpen
                    ? 'rotate-45 bg-primary text-white'
                  : 'bg-[#f4f2fd] text-[#5446dc]'
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
                className="px-5.5 pb-5 pl-[62px] text-[13.5px] leading-relaxed text-[#6f7090] [&_b]:font-bold [&_b]:text-[#33344c]"
                dangerouslySetInnerHTML={{ __html: f.a }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
