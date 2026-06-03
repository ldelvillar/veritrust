import type { Metadata } from 'next';

import { CONFIG } from '@/config';

import HelpArticleCatalog from './_components/HelpArticleCatalog';
import HelpCategories from './_components/HelpCategories';
import HelpContactStrip from './_components/HelpContactStrip';
import HelpFaqSection from './_components/HelpFaqSection';
import HelpHero from './_components/HelpHero';
import HelpSteps from './_components/HelpSteps';
import { ARTICLES, CATEGORIES, FAQ, POPULAR, STEPS } from './helpContent';

export const metadata: Metadata = {
  title: 'Ayuda | VeriTrust',
  description:
    'Centro de ayuda de VeriTrust con guía de uso, preguntas frecuentes y soporte.',
};

export default function AyudaPage() {
  return (
    <div className="mx-auto w-full max-w-270 px-4 py-8 md:px-8 md:py-10">
      <HelpHero articles={ARTICLES} faq={FAQ} popular={POPULAR} />
      <HelpCategories articles={ARTICLES} categories={CATEGORIES} />
      <HelpArticleCatalog articles={ARTICLES} categories={CATEGORIES} />
      <HelpSteps steps={STEPS} />
      <HelpFaqSection faq={FAQ} />
      <HelpContactStrip email={CONFIG.email} />
    </div>
  );
}
