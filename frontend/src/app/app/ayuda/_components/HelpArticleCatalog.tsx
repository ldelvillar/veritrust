import type { HelpArticle, HelpCategory } from '../helpContent';
import HelpCategoryIcon from './HelpCategoryIcon';

interface HelpArticleCatalogProps {
  articles: HelpArticle[];
  categories: HelpCategory[];
}

function formatArticleCount(count: number) {
  return count === 1 ? '1 artículo' : `${count} artículos`;
}

export default function HelpArticleCatalog({
  articles,
  categories,
}: HelpArticleCatalogProps) {
  return (
    <>
      <div className="mt-10 mb-2" id="articulos">
        <div className="mb-1 text-[11px] font-bold tracking-[0.13em] text-primary uppercase">
          Artículos
        </div>
        <h2 className="text-[20px] font-bold tracking-[-0.02em] text-[#15162c]">
          Guías del centro de ayuda
        </h2>
        <p className="mt-1 text-[13.5px] text-[#7e7f99]">
          Todos los artículos organizados por categoría para consultar pasos,
          criterios y solución de problemas.
        </p>
      </div>

      <div className="mt-4 space-y-5">
        {categories.map(category => {
          const categoryArticles = articles.filter(
            article => article.category === category.title
          );

          return (
            <section
              key={category.title}
              id={category.slug}
              className="rounded-[18px] border border-[#e8e6f4] bg-white p-5.5 shadow-sm"
            >
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <div
                  className="grid size-10 place-items-center rounded-xl"
                  style={{ background: category.tint, color: category.color }}
                >
                  <HelpCategoryIcon name={category.icon} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-[16px] font-bold text-[#15162c]">
                    {category.title}
                  </h3>
                  <p className="mt-0.5 text-[12.5px] font-semibold text-[#8b8ca6]">
                    {formatArticleCount(categoryArticles.length)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {categoryArticles.map(article => (
                  <article
                    key={article.id}
                    id={article.id}
                    className="scroll-mt-24 rounded-[14px] border border-[#eceaf6] bg-[#fbfafe] p-4 transition hover:border-[#d0cdf0] hover:bg-white"
                  >
                    <h4 className="text-[14px] leading-snug font-bold text-[#15162c]">
                      {article.title}
                    </h4>
                    <p className="mt-2 text-[12.8px] leading-relaxed text-[#6f7090]">
                      {article.summary}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {article.tags.map(tag => (
                        <span
                          key={tag}
                          className="rounded-[7px] border border-[#e8e6f4] bg-white px-2.5 py-1 text-[10.5px] font-bold text-[#656682]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </>
  );
}
