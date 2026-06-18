import type { SVGProps } from 'react';

export default function PlusBoxIcon(props: SVGProps<SVGSVGElement>) {
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
      <rect x="3" y="3" width="18" height="18" rx="5.5" />
      <path d="M12 8.2v7.6M8.2 12h7.6" />
    </svg>
  );
}
