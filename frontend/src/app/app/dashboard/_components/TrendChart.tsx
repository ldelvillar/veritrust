interface TrendPoint {
  date: string;
  total: number;
  average_confidence: number;
}

export default function TrendChart({ data }: { data: TrendPoint[] }) {
  const W = 720,
    H = 270,
    padL = 16,
    padR = 16,
    padT = 22,
    padB = 34;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const maxN = Math.max(1, ...data.map(t => t.total));
  const niceMax = Math.ceil(maxN / 4) * 4;
  const slot = plotW / (data.length || 1);
  const barW = slot * 0.4;
  const grid = [0, 0.25, 0.5, 0.75, 1];

  const linePts = data.map((t, i) => ({
    x: padL + i * slot + slot / 2,
    y: padT + (1 - t.average_confidence / 100) * plotH,
  }));
  const lineD = linePts
    .map((q, i) => `${i ? 'L' : 'M'}${q.x.toFixed(1)} ${q.y.toFixed(1)}`)
    .join(' ');

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Tendencia de análisis"
      className="w-full overflow-visible"
      style={{ display: 'block', height: 'auto' }}
    >
      <defs>
        <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8579f0" />
          <stop offset="1" stopColor="#5e50e0" />
        </linearGradient>
      </defs>

      {grid.map((g, i) => {
        const y = padT + g * plotH;
        return (
          <g key={i}>
            <line
              x1={padL}
              y1={y.toFixed(1)}
              x2={W - padR}
              y2={y.toFixed(1)}
              stroke="#e8e6f4"
              strokeWidth={1}
              strokeDasharray={i === grid.length - 1 ? '0' : '3 4'}
            />
            <text
              x={padL}
              y={(y - 5).toFixed(1)}
              fill="#a3a4ba"
              fontFamily="Mulish,system-ui,sans-serif"
              fontSize={11}
              fontWeight={600}
            >
              {Math.round(niceMax * (1 - g))}
            </text>
          </g>
        );
      })}

      {data.map((t, i) => {
        const h = (t.total / niceMax) * plotH;
        const x = padL + i * slot + slot / 2 - barW / 2;
        const y = padT + plotH - h;
        const label = new Date(t.date).toLocaleDateString('es-ES', {
          day: 'numeric',
          month: 'numeric',
        });
        return (
          <g
            key={t.date}
            className="cursor-pointer"
            style={{ transition: '.16s' }}
          >
            <rect
              x={x.toFixed(1)}
              y={y.toFixed(1)}
              width={barW.toFixed(1)}
              height={Math.max(h, 1).toFixed(1)}
              rx={5}
              fill="url(#barGrad)"
            />
            <text
              x={(x + barW / 2).toFixed(1)}
              y={H - 12}
              fill="#a3a4ba"
              fontFamily="Mulish,system-ui,sans-serif"
              fontSize={11}
              fontWeight={600}
              textAnchor="middle"
            >
              {label}
            </text>
          </g>
        );
      })}

      {data.length > 1 && (
        <>
          <path
            d={lineD}
            fill="none"
            stroke="#5446dc"
            strokeWidth={2.6}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {linePts.map((q, i) => (
            <circle
              key={i}
              cx={q.x.toFixed(1)}
              cy={q.y.toFixed(1)}
              r={3.4}
              fill="#fff"
              stroke="#5446dc"
              strokeWidth={2.4}
            />
          ))}
        </>
      )}
    </svg>
  );
}
