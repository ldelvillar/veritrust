import type { SVGProps } from 'react';

export default function GlobeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M3.5 12h17M12 3c2.4 2.4 2.4 15.6 0 18M12 3c-2.4 2.4-2.4 15.6 0 18" />
    </svg>
  );
}
