'use client';

import { useMemo, useRef, useState } from 'react';

import ArrowRightIcon from '@/assets/ArrowRight';
import CrossIcon from '@/assets/Cross';
import Magnifier from '@/assets/Magnifier';

import type { HelpArticle, HelpFaqItem } from '../helpContent';

interface HelpSearchProps {
  articles: HelpArticle[];
  faq: HelpFaqItem[];
  popular: string[];
}

interface SearchRecord {
  id: string;
  kind: 'Artículo' | 'FAQ';
  title: string;
  category: string;
  summary: string;
  href: string;
  searchable: string;
}

const MAX_RESULTS = 8;

function normalizeSearchText(value: string) {
  return value
    .toLocaleLowerCase('es')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ');
}

export default function HelpSearch({
  articles,
  faq,
  popular,
}: HelpSearchProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const records = useMemo<SearchRecord[]>(
    () => [
      ...articles.map(article => ({
        id: article.id,
        kind: 'Artículo' as const,
        title: article.title,
        category: article.category,
        summary: article.summary,
        href: `#${article.id}`,
        searchable: normalizeSearchText(
          [
            article.title,
            article.category,
            article.summary,
            ...article.tags,
          ].join(' ')
        ),
      })),
      ...faq.map((item, index) => {
        const summary = stripHtml(item.a);

        return {
          id: `faq-${index}`,
          kind: 'FAQ' as const,
          title: item.q,
          category: item.cat,
          summary,
          href: '#faq',
          searchable: normalizeSearchText(
            [item.q, item.cat, summary].join(' ')
          ),
        };
      }),
    ],
    [articles, faq]
  );

  const trimmedQuery = query.trim();
  const normalizedTerms = normalizeSearchText(trimmedQuery)
    .split(/\s+/)
    .filter(Boolean);

  const results =
    normalizedTerms.length === 0
      ? []
      : records
          .filter(record =>
            normalizedTerms.every(term => record.searchable.includes(term))
          )
          .slice(0, MAX_RESULTS);

  function focusPopular(term: string) {
    setQuery(term);
    inputRef.current?.focus();
  }

  function navigateToFirstResult() {
    const firstResult = results[0];

    if (!firstResult) {
      return;
    }

    const target = document.getElementById(firstResult.href.slice(1));
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    window.history.replaceState(null, '', firstResult.href);
  }

  return (
    <div className="mt-5 max-w-150">
      <form
        onSubmit={event => {
          event.preventDefault();
          navigateToFirstResult();
        }}
        className="flex items-center gap-2 rounded-2xl bg-white px-3 py-2 shadow-[0_14px_34px_rgba(36,24,90,.24)] sm:gap-3 sm:px-4.5"
      >
        <label htmlFor="help-search" className="sr-only">
          Buscar en el centro de ayuda
        </label>
        <Magnifier className="size-4.5 shrink-0 text-[#9698b1]" />
        <input
          ref={inputRef}
          id="help-search"
          type="text"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Busca en guías, preguntas frecuentes y fuentes..."
          className="min-w-0 flex-1 py-2.5 text-[14.5px] text-[#33344c] outline-none placeholder:text-[#b0b1c8]"
        />
        {query.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              inputRef.current?.focus();
            }}
            aria-label="Limpiar búsqueda"
            className="grid size-8 shrink-0 place-items-center rounded-lg text-[#9698b1] transition hover:bg-[#f4f2fd] hover:text-[#5446dc]"
          >
            <CrossIcon className="size-4" />
          </button>
        )}
        <button
          type="submit"
          className="flex shrink-0 items-center gap-2 rounded-[11px] bg-primary px-3 py-2.5 text-[13.5px] font-semibold text-white transition hover:bg-primary/90 sm:px-4"
        >
          <ArrowRightIcon
            width="15"
            height="15"
            strokeWidth="2.2"
            className="hidden sm:block"
          />
          Buscar
        </button>
      </form>

      {trimmedQuery.length > 0 && (
        <div className="mt-3 overflow-hidden rounded-2xl border border-white/70 bg-white text-[#15162c] shadow-[0_16px_34px_rgba(36,24,90,.2)]">
          {results.length > 0 ? (
            <div className="max-h-80 overflow-y-auto">
              {results.map(result => (
                <a
                  key={`${result.kind}-${result.id}`}
                  href={result.href}
                  onClick={() => setQuery(result.title)}
                  className="block border-t border-[#eceaf6] px-4 py-3.5 text-left transition first:border-t-0 hover:bg-[#faf9fe]"
                >
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="rounded-[7px] bg-[#efedfc] px-2 py-0.5 text-[10.5px] font-bold tracking-[0.04em] text-[#5446dc] uppercase">
                      {result.kind}
                    </span>
                    <span className="text-[11.5px] font-bold text-[#8b8ca6]">
                      {result.category}
                    </span>
                  </div>
                  <div className="text-[14px] leading-snug font-bold text-[#15162c]">
                    {result.title}
                  </div>
                  <p className="mt-1 line-clamp-2 text-[12.5px] leading-relaxed text-[#6f7090]">
                    {result.summary}
                  </p>
                </a>
              ))}
            </div>
          ) : (
            <div className="px-4 py-4 text-[13.5px] font-medium text-[#6f7090]">
              No hay resultados para «{trimmedQuery}».
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2.5">
        <span className="text-[12.5px] font-bold text-white/70">
          Populares:
        </span>
        {popular.map(term => (
          <button
            key={term}
            type="button"
            onClick={() => focusPopular(term)}
            className="rounded-full border border-white/16 bg-white/14 px-3.5 py-1.5 text-[12.5px] font-semibold text-white transition hover:bg-white/24"
          >
            {term}
          </button>
        ))}
      </div>
    </div>
  );
}
