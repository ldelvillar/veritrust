import type { SVGProps } from 'react';

export default function BuildingIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-6h6v6" />
    </svg>
  );
}
