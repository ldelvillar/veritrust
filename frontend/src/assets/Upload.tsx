import type { SVGProps } from 'react';

export default function UploadIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M12 16V4M7 9l5-5 5 5M5 18v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1" />
    </svg>
  );
}
