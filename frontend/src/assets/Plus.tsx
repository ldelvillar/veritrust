import type { SVGProps } from 'react';

export default function PlusIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.4}
      strokeLinecap="round"
      {...props}
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
