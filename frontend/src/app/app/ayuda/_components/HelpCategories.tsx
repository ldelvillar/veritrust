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
        <div className="mb-1 text-[11px] font-bold tracking-[0.13em] text-primary uppercase">
          Explora
        </div>
        <h2 className="text-[20px] font-bold tracking-[-0.02em] text-[#15162c]">
          Explora por categoría
        </h2>
        <p className="mt-1 text-[13.5px] text-[#7e7f99]">
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
              className="group flex cursor-pointer flex-col gap-3 rounded-[18px] border border-[#e8e6f4] bg-white p-5.5 shadow-sm transition hover:-translate-y-0.5 hover:border-[#d0cdf0] hover:shadow-md"
            >
              <div
                className="grid size-11 place-items-center rounded-[13px]"
                style={{ background: category.tint, color: category.color }}
              >
                <HelpCategoryIcon name={category.icon} />
              </div>
              <h3 className="text-[15px] font-bold text-[#15162c]">
                {category.title}
              </h3>
              <p className="text-[13px] leading-relaxed text-[#7e7f99]">
                {category.desc}
              </p>
              <div className="mt-auto flex items-center justify-between pt-1">
                <span className="text-[12px] font-bold text-[#b0b1c8]">
                  {formatArticleCount(count)}
                </span>
                <ArrowRightIcon
                  className="transition group-hover:translate-x-0.5 group-hover:stroke-[#5446dc]"
                  width={17}
                  height={17}
                  stroke="#b0b1c8"
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
