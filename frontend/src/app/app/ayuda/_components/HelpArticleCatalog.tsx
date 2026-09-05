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
        <div className="mb-1 text-2xs font-bold tracking-[0.13em] text-primary uppercase">
          Artículos
        </div>
        <h2 className="text-xl font-bold tracking-[-0.02em] text-ink">
          Guías del centro de ayuda
        </h2>
        <p className="mt-1 text-sm text-muted">
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
              className="rounded-2xl border border-line bg-white p-5.5 shadow-sm"
            >
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <div className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary">
                  <HelpCategoryIcon name={category.icon} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-base font-bold text-ink">
                    {category.title}
                  </h3>
                  <p className="mt-0.5 text-xs font-semibold text-muted">
                    {formatArticleCount(categoryArticles.length)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {categoryArticles.map(article => (
                  <article
                    key={article.id}
                    id={article.id}
                    className="scroll-mt-24 rounded-xl border border-line bg-surface-subtle p-4 transition hover:border-line-strong hover:bg-white"
                  >
                    <h4 className="text-sm leading-snug font-bold text-ink">
                      {article.title}
                    </h4>
                    <p className="mt-2 text-xs leading-relaxed text-muted">
                      {article.summary}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {article.tags.map(tag => (
                        <span
                          key={tag}
                          className="rounded-lg border border-line bg-white px-2.5 py-1 text-2xs font-bold text-muted"
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
