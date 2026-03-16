import type { SVGProps } from 'react';

export default function Robot(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="50"
      height="50"
      viewBox="0 0 48 48"
      {...props}
    >
      <g fill="none">
        <rect
          width="30"
          height="24"
          x="9"
          y="18"
          stroke="currentColor"
          strokeWidth="4"
          rx="2"
        />
        <circle cx="17" cy="26" r="2" fill="currentColor" />
        <circle cx="31" cy="26" r="2" fill="currentColor" />
        <path
          fill="currentColor"
          d="M20 32a2 2 0 1 0 0 4zm8 4a2 2 0 1 0 0-4zm-8 0h8v-4h-8z"
        />
        <path
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="4"
          d="M24 10v8M4 26v8m40-8v8"
        />
        <circle cx="24" cy="8" r="2" stroke="currentColor" strokeWidth="4" />
      </g>
    </svg>
  );
}
