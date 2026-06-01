import type { SVGProps } from 'react';

export default function Chevron(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      className="size-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      {...props}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        d="M6 9l6 6 6-6"
      />
    </svg>
  );
}
