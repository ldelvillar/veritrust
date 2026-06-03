import type { HelpArticle, HelpFaqItem } from '../helpContent';
import HelpSearch from './HelpSearch';

interface HelpHeroProps {
  articles: HelpArticle[];
  faq: HelpFaqItem[];
  popular: string[];
}

export default function HelpHero({ articles, faq, popular }: HelpHeroProps) {
  return (
    <div className="relative mb-8 overflow-hidden rounded-[22px] bg-[linear-gradient(125deg,#6557e6_0%,#5345d8_52%,#4a3cc9_100%)] px-8 py-11 text-white shadow-[0_18px_44px_rgba(83,69,216,.28)] md:px-11">
      <div className="pointer-events-none absolute -top-20 -right-16 size-72 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,.16),transparent_62%)]" />
      <div className="pointer-events-none absolute -bottom-36 left-[38%] size-64 rounded-full bg-[radial-gradient(circle,rgba(124,110,240,.5),transparent_60%)]" />

      <div className="relative z-10 max-w-150">
        <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/15 px-3.5 py-1.5 text-[12px] font-bold tracking-widest uppercase">
          Centro de ayuda
        </span>
        <h1 className="mb-2.5 text-[30px] leading-[1.08] font-bold tracking-[-0.025em] text-white md:text-[34px]">
          ¿En qué podemos ayudarte?
        </h1>
        <p className="max-w-125 text-[15px] leading-relaxed font-medium text-white/85">
          Guías, fuentes y respuestas para sacar el máximo partido a la
          verificación de información médica.
        </p>
        <HelpSearch articles={articles} faq={faq} popular={popular} />
      </div>
    </div>
  );
}
