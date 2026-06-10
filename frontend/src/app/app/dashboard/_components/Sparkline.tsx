export default function Sparkline({
  data,
  color,
}: {
  data: number[];
  color: string;
}) {
  const W = 74,
    H = 30,
    p = 3;
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const rng = max - min || 1;
  const pts = data.map((v, i) => ({
    x: p + (i / (data.length - 1)) * (W - 2 * p),
    y: p + (1 - (v - min) / rng) * (H - 2 * p),
  }));
  const d = pts
    .map((q, i) => `${i ? 'L' : 'M'}${q.x.toFixed(1)} ${q.y.toFixed(1)}`)
    .join(' ');
  const area = `${d} L ${(W - p).toFixed(1)} ${H - p} L ${p} ${H - p} Z`;
  const gid = `sg-${color.replace('#', '')}`;
  const last = pts[pts.length - 1];
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ width: 74, height: 30, flexShrink: 0 }}
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity={0.22} />
          <stop offset="1" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx={last.x.toFixed(1)}
        cy={last.y.toFixed(1)}
        r={2.6}
        fill={color}
      />
    </svg>
  );
}
