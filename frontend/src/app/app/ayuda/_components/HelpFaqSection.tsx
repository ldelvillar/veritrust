import HelpFaq from './HelpFaq';

import type { HelpFaqItem } from '../helpContent';

interface HelpFaqSectionProps {
  faq: HelpFaqItem[];
}

export default function HelpFaqSection({ faq }: HelpFaqSectionProps) {
  return (
    <>
      <div className="mt-10 mb-2" id="faq">
        <div className="mb-1 text-2xs font-bold tracking-[0.13em] text-primary uppercase">
          Dudas
        </div>
        <h2 className="text-xl font-bold tracking-[-0.02em] text-ink">
          Preguntas frecuentes
        </h2>
        <p className="mt-1 text-sm text-muted">
          Lo que más nos preguntan sobre el uso, la privacidad y los informes.
        </p>
      </div>

      <div className="mt-4">
        <HelpFaq items={faq} />
      </div>
    </>
  );
}
