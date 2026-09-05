import ArrowRightIcon from '@/assets/ArrowRight';

import type { HelpArticle, HelpCategory } from '../helpContent';
import HelpCategoryIcon from './HelpCategoryIcon';

interface HelpCategoriesProps {
  articles: HelpArticle[];
  categories: HelpCategory[];
}

function formatArticleCount(count: number) {
  return count === 1 ? '1 artículo' : `${count} artículos`;
}

export default function HelpCategories({
  articles,
  categories,
}: HelpCategoriesProps) {
  return (
    <>
      <div className="mt-8 mb-2">
        <div className="mb-1 text-2xs font-bold tracking-[0.13em] text-primary uppercase">
          Explora
        </div>
        <h2 className="text-xl font-bold tracking-[-0.02em] text-ink">
          Explora por categoría
        </h2>
        <p className="mt-1 text-sm text-muted">
          Seis áreas que cubren todo el ciclo: desde tu primer análisis hasta la
          facturación.
        </p>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map(category => {
          const count = articles.filter(
            article => article.category === category.title
          ).length;

          return (
            <a
              key={category.title}
              href={`#${category.slug}`}
              className="group flex cursor-pointer flex-col gap-3 rounded-2xl border border-line bg-white p-5.5 shadow-sm transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-md"
            >
              <div className="grid size-11 place-items-center rounded-xl bg-primary-soft text-primary">
                <HelpCategoryIcon name={category.icon} />
              </div>
              <h3 className="text-base font-bold text-ink">{category.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {category.desc}
              </p>
              <div className="mt-auto flex items-center justify-between pt-1">
                <span className="text-xs font-bold text-muted">
                  {formatArticleCount(count)}
                </span>
                <ArrowRightIcon
                  className="transition group-hover:translate-x-0.5 group-hover:stroke-accent"
                  width={17}
                  height={17}
                  stroke="var(--color-faint)"
                  strokeWidth={2.1}
                />
              </div>
            </a>
          );
        })}
      </div>
    </>
  );
}
