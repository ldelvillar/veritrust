import type { SVGProps } from 'react';

export default function TypeIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M4 7V5h16v2M9 19h6M12 5v14" />
    </svg>
  );
}
