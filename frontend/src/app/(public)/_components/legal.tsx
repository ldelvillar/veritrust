import { SITE_CONFIG } from '@/config/site';

/** Shared link and list styles for the legal pages. */
export const legalLinkClass =
  'text-primary transition duration-300 hover:text-primary/90';
export const legalListClass =
  'mt-3 list-disc space-y-2 pl-6 text-base leading-7 text-body';

/** Mailto link to the contact address of the service's holder. */
export function EmailLink() {
  return (
    <a href={`mailto:${SITE_CONFIG.email}`} className={legalLinkClass}>
      {SITE_CONFIG.email}
    </a>
  );
}
