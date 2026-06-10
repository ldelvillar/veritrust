'use client';

import { useEffect, useState } from 'react';

export default function CredibilityGauge({ score }: { score: number | null }) {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    // Incierto (score null): aro sin rellenar. Con puntuación: animamos al valor.
    const target =
      score === null
        ? circumference
        : circumference * (1 - Math.min(Math.max(score, 0), 100) / 100);
    const id = setTimeout(() => setOffset(target), 160);
    return () => clearTimeout(id);
  }, [score, circumference]);

  return (
    <div className="relative size-43">
      <svg width="172" height="172" className="-rotate-90">
        <circle
          cx="86"
          cy="86"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,.22)"
          strokeWidth="14"
        />
        {score !== null && (
          <circle
            cx="86"
            cy="86"
            r={radius}
            fill="none"
            stroke="#fff"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {score === null ? (
          <>
            <span className="text-5xl leading-none font-black text-white">
              ?
            </span>
            <span className="mt-1 text-[13px] font-semibold tracking-wide text-white/80">
              Sin puntuación
            </span>
          </>
        ) : (
          <>
            <span className="text-5xl leading-none font-black text-white">
              {score}
            </span>
            <span className="mt-1 text-[13px] font-semibold tracking-wide text-white/80">
              / 100
            </span>
          </>
        )}
      </div>
    </div>
  );
}
