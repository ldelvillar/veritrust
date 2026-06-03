import type { SVGProps } from 'react';

export default function StarIcon(props: SVGProps<SVGSVGElement>) {
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
      <path d="M12 2l2.09 6.26L20 10l-5 4.87L16.18 22 12 18.77 7.82 22 9 14.87 4 10l5.91-1.74z" />
    </svg>
  );
}
