'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import Magnifier from '@/assets/Magnifier';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { paths } from '@/types/api';

type DashboardPayload =
  paths['/dashboard/summary']['get']['responses']['200']['content']['application/json'];
type DashboardAlertItem = DashboardPayload['alerts'][number];

// ── Icon components ──────────────────────────────────────────────────────────

function IcList({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <line x1="8" y1="6" x2="20" y2="6" />
      <line x1="8" y1="12" x2="20" y2="12" />
      <line x1="8" y1="18" x2="20" y2="18" />
      <circle cx="3.5" cy="6" r="1" />
      <circle cx="3.5" cy="12" r="1" />
      <circle cx="3.5" cy="18" r="1" />
    </svg>
  );
}

function IcShield({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IcSparkle({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
      <path d="M19 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
    </svg>
  );
}

function IcWarn({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
    </svg>
  );
}

function IcArrowUp({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M6 14l6-6 6 6" />
    </svg>
  );
}

function IcArrowDown({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M6 10l6 6 6-6" />
    </svg>
  );
}

function IcArrowRight({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function QuestionIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.7M12 17h.01" />
    </svg>
  );
}

// ── Tooltip hint ──────────────────────────────────────────────────────────────

function InfoHint({ label, text }: { label: string; text: string }) {
  return (
    <span className="group relative inline-flex shrink-0">
      <button
        type="button"
        aria-label={`Cómo se calcula: ${label}`}
        className="grid size-4 place-items-center rounded-full text-slate-300 transition hover:text-slate-500 focus:text-slate-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        <QuestionIcon className="size-4" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute top-full right-0 z-10 mt-2 w-56 rounded-lg bg-slate-900 px-3 py-2 text-left text-xs leading-snug font-medium text-white opacity-0 shadow-lg transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}

// ── Sparkline ─────────────────────────────────────────────────────────────────

function Sparkline({ data, color }: { data: number[]; color: string }) {
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

// ── KPI card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  tint: string;
  color: string;
  delta?: { dir: 'up' | 'down'; value: string };
  spark?: number[];
  hint: string;
}

function KpiCard({
  label,
  value,
  sub,
  icon,
  tint,
  color,
  delta,
  spark,
  hint,
}: KpiCardProps) {
  return (
    <article className="relative flex flex-col gap-3 overflow-hidden rounded-[20px] border border-[#e8e6f4] bg-white p-5 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(60,50,140,.16)]">
      <div className="flex items-center gap-3">
        <div
          className="grid size-[38px] shrink-0 place-items-center rounded-[11px]"
          style={{ background: tint, color }}
        >
          {icon}
        </div>
        <p
          className="text-[11px] leading-tight font-bold tracking-[.09em] uppercase"
          style={{ color: '#9698b1' }}
        >
          {label}
        </p>
        <div className="ml-auto">
          <InfoHint label={label} text={hint} />
        </div>
      </div>

      <p className="font-display text-[34px] leading-none font-bold tracking-[-0.03em] text-[#15162c]">
        {value}
      </p>

      <div className="mt-0.5 flex items-end justify-between gap-2">
        <div className="flex flex-col gap-1.5">
          {delta && (
            <span
              className="inline-flex items-center gap-1 rounded-full px-[9px] py-1 text-[12px] font-bold"
              style={
                delta.dir === 'up'
                  ? { color: '#0e8e5b', background: '#def4ea' }
                  : { color: '#c23552', background: '#fbe4e8' }
              }
            >
              {delta.dir === 'up' ? (
                <IcArrowUp className="size-3" />
              ) : (
                <IcArrowDown className="size-3" />
              )}
              {delta.value}
              <span style={{ fontWeight: 600, opacity: 0.8 }}>sem.</span>
            </span>
          )}
          <span
            className="text-[11.5px] font-semibold"
            style={{ color: '#a3a4ba' }}
          >
            {sub}
          </span>
        </div>
        {spark && <Sparkline data={spark} color={color} />}
      </div>
    </article>
  );
}

// ── Trend chart ───────────────────────────────────────────────────────────────

interface TrendPoint {
  date: string;
  total: number;
  average_confidence: number;
}

function TrendChart({ data }: { data: TrendPoint[] }) {
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

// ── Source breakdown ──────────────────────────────────────────────────────────

const SOURCE_META: Record<string, { label: string; color: string }> = {
  text: { label: 'Texto', color: '#6356e6' },
  url: { label: 'Enlace', color: '#2c97e8' },
  file: { label: 'Archivo', color: '#13b877' },
  pdf: { label: 'Archivo', color: '#13b877' },
};

function SourcesCard({
  items,
}: {
  items: DashboardPayload['source_breakdown'];
}) {
  const total = items.reduce((a, s) => a + s.total, 0) || 1;
  const wavg = Math.round(
    items.reduce((a, s) => a + s.average_confidence * s.total, 0) / total
  );

  return (
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
            Fuentes
          </h2>
          <p
            className="mt-1 text-[13px] leading-snug"
            style={{ color: '#7e7f99' }}
          >
            Reparto por tipo de entrada.
          </p>
        </div>
        <span
          className="shrink-0 rounded-full border border-[#e7e3fb] bg-[#f4f2fd] px-[11px] py-[6px] text-[11.5px] font-bold"
          style={{ color: '#5446dc' }}
        >
          {total} análisis
        </span>
      </div>

      {/* Segmented bar */}
      <div className="mb-5 flex h-[14px] gap-0.5 overflow-hidden rounded-full">
        {items.map(s => {
          const meta = SOURCE_META[s.source_type] ?? {
            label: s.source_type,
            color: '#9698b1',
          };
          return (
            <div
              key={s.source_type}
              style={{ flex: s.total, background: meta.color }}
            />
          );
        })}
      </div>

      <div className="flex flex-col">
        {items.map((s, idx) => {
          const meta = SOURCE_META[s.source_type] ?? {
            label: s.source_type,
            color: '#9698b1',
          };
          return (
            <div
              key={s.source_type}
              className="flex items-center gap-3.5 py-3"
              style={{ borderTop: idx === 0 ? 'none' : '1px solid #e8e6f4' }}
            >
              <span
                className="size-[11px] shrink-0 rounded-[4px]"
                style={{ background: meta.color }}
              />
              <span className="shrink-0 text-[14px] font-bold text-[#15162c]">
                {meta.label}
              </span>
              <div
                className="h-2 flex-1 overflow-hidden rounded-full"
                style={{ background: '#eeedf8' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(s.total / total) * 100}%`,
                    background: meta.color,
                  }}
                />
              </div>
              <span className="font-display w-7 shrink-0 text-right text-[14px] font-bold text-[#15162c]">
                {s.total}
              </span>
            </div>
          );
        })}
      </div>

      {items.length > 0 && (
        <div className="mt-4 flex items-center justify-between border-t border-[#e8e6f4] pt-4">
          <span
            className="text-[12.5px] font-semibold"
            style={{ color: '#7e7f99' }}
          >
            Confianza media del periodo
          </span>
          <span className="text-[13.5px] font-bold text-[#15162c]">
            {wavg}%
          </span>
        </div>
      )}
    </section>
  );
}

// ── Domain breakdown ──────────────────────────────────────────────────────────

function domainCredibility(avgConf: number): {
  label: string;
  cls: 'ok' | 'warn' | 'bad';
} {
  if (avgConf >= 75) return { label: 'Alta', cls: 'ok' };
  if (avgConf >= 50) return { label: 'Media', cls: 'warn' };
  return { label: 'Baja', cls: 'bad' };
}

const CRED_STYLES = {
  ok: { color: '#0e8e5b', background: '#def4ea' },
  warn: { color: '#b07a16', background: '#fbefda' },
  bad: { color: '#c23552', background: '#fbe4e8' },
};

function DomainsCard({
  items,
}: {
  items: DashboardPayload['domain_breakdown'];
}) {
  const maxCount = Math.max(1, ...items.map(d => d.total));

  return (
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5">
        <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
          Dominios frecuentes
        </h2>
        <p
          className="mt-1 text-[13px] leading-snug"
          style={{ color: '#7e7f99' }}
        >
          Top de enlaces analizados por frecuencia.
        </p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium" style={{ color: '#7e7f99' }}>
          No hay dominios registrados todavía.
        </p>
      ) : (
        <div className="flex flex-col">
          {items.map((item, idx) => {
            const cred = domainCredibility(item.average_confidence);
            const init = item.domain[0]?.toUpperCase() ?? '?';
            return (
              <div
                key={item.domain}
                className="flex items-center gap-3.5 py-3.5"
                style={{
                  borderTop: idx === 0 ? 'none' : '1px solid #e8e6f4',
                  paddingTop: idx === 0 ? 2 : undefined,
                }}
              >
                <div
                  className="font-display grid size-9 shrink-0 place-items-center rounded-[10px] border border-[#e8e6f4] text-[14px] font-bold uppercase"
                  style={{ background: '#faf9fe', color: '#7e7f99' }}
                >
                  {init}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-[14px] font-bold text-[#15162c]">
                      {item.domain}
                    </span>
                    <span
                      className="shrink-0 text-[12px] font-semibold"
                      style={{ color: '#a3a4ba' }}
                    >
                      · {item.total} análisis
                    </span>
                  </div>
                  <div
                    className="mt-2 h-1.5 overflow-hidden rounded-full"
                    style={{ background: '#eeedf8' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(item.total / maxCount) * 100}%`,
                        background: 'linear-gradient(90deg,#8579f0,#5e50e0)',
                      }}
                    />
                  </div>
                </div>
                <span
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-[11px] py-[5px] text-[12px] font-bold"
                  style={CRED_STYLES[cred.cls]}
                >
                  <span
                    className="size-2 rounded-full"
                    style={{ background: 'currentColor' }}
                  />
                  {cred.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ── Alerts ────────────────────────────────────────────────────────────────────

function alertVerdict(item: DashboardAlertItem): {
  label: string;
  tone: 'bad' | 'warn';
} {
  const score = item.credibility ?? 0;
  if (item.label === 'falsa' || score < 40)
    return { label: 'Engañoso', tone: 'bad' };
  return { label: 'Dudoso', tone: 'warn' };
}

const ALERT_STYLES = {
  bad: {
    card: { background: '#fdf3f5', borderColor: '#f3d2da' },
    score: 'linear-gradient(150deg,#e2607a,#d23c5d)',
    verdict: { color: '#c23552', background: '#fbe4e8' },
  },
  warn: {
    card: { background: '#fdf8ef', borderColor: '#f1e2c2' },
    score: 'linear-gradient(150deg,#e8b057,#d98e29)',
    verdict: { color: '#b07a16', background: '#fbefda' },
  },
};

function getAlertTitle(item: DashboardAlertItem): string {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
}

function AlertsCard({ items }: { items: DashboardAlertItem[] }) {
  return (
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
            Alertas recientes
          </h2>
          <p
            className="mt-1 text-[13px] leading-snug"
            style={{ color: '#7e7f99' }}
          >
            Últimos análisis con baja credibilidad detectada.
          </p>
        </div>
        {items.length > 0 && (
          <span
            className="shrink-0 rounded-full border border-[#e7e3fb] bg-[#f4f2fd] px-[11px] py-[6px] text-[11.5px] font-bold"
            style={{ color: '#5446dc' }}
          >
            {items.length} nuevas
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium" style={{ color: '#7e7f99' }}>
          No hay alertas por ahora.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {items.map(item => {
              const { label, tone } = alertVerdict(item);
              const st = ALERT_STYLES[tone];
              const score = item.credibility ?? 0;
              const date = new Date(item.created_at).toLocaleString('es-ES', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              });
              return (
                <Link
                  key={item.id}
                  href={`/app/analisis/${item.id}`}
                  className="group flex items-start gap-3.5 rounded-[14px] border p-[17px] transition-all duration-150 hover:shadow-sm"
                  style={st.card}
                >
                  <div
                    className="flex size-12 shrink-0 flex-col items-center justify-center rounded-[13px] text-white"
                    style={{ background: st.score }}
                  >
                    <span className="font-display text-[17px] leading-none font-bold">
                      {score}
                    </span>
                    <span className="mt-0.5 text-[9px] font-semibold opacity-85">
                      /100
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-[14px] leading-[1.45] font-bold text-[#15162c]">
                      {getAlertTitle(item)}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2.5">
                      <span
                        className="rounded-[6px] px-[9px] py-[3px] text-[10.5px] font-bold tracking-[.05em] uppercase"
                        style={st.verdict}
                      >
                        {label}
                      </span>
                      <span
                        className="text-[12px] font-semibold"
                        style={{ color: '#7e7f99' }}
                      >
                        {date}
                      </span>
                    </div>
                  </div>

                  <div
                    className="grid size-[34px] shrink-0 place-items-center self-center rounded-[10px] border border-[#e8e6f4] bg-white transition-transform duration-150 group-hover:translate-x-0.5"
                    style={{ color: '#a3a4ba' }}
                  >
                    <IcArrowRight className="size-4" />
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="mt-4 flex justify-center">
            <Link
              href="/app/historial"
              className="font-display inline-flex items-center gap-2 text-[13.5px] font-semibold"
              style={{ color: '#5446dc' }}
            >
              Ver todas las alertas <IcArrowRight className="size-4" />
            </Link>
          </div>
        </>
      )}
    </section>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-12">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-[#e8e6f4] bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-[#eeebfc] text-[#6356e6]">
          <Magnifier className="size-7" />
        </div>
        <h1 className="mt-5 text-2xl font-black tracking-tight text-[#15162c]">
          Empieza tu primer análisis
        </h1>
        <p className="mt-2 text-sm font-medium" style={{ color: '#7e7f99' }}>
          Tu panel se llenará con métricas, tendencias y alertas en cuanto
          verifiques tu primer contenido médico.
        </p>
        <Link
          href="/app/analisis"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-[#6356e6] px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_rgba(99,86,230,.32)] transition hover:bg-[#5446dc] focus:ring-4 focus:ring-[#6356e6]/20 focus:outline-none"
        >
          Analizar contenido
        </Link>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface DashboardClientProps {
  initialData: DashboardPayload;
}

export default function DashboardClient({ initialData }: DashboardClientProps) {
  const { data } = useApiQuery<DashboardPayload>('/dashboard/summary', {
    fallbackData: initialData,
  });
  const dashboard = data ?? initialData;

  const sparkTotal = useMemo(
    () => dashboard.trend.slice(-7).map(t => t.total),
    [dashboard.trend]
  );
  const sparkConf = useMemo(
    () => dashboard.trend.slice(-7).map(t => t.average_confidence),
    [dashboard.trend]
  );
  const delta = dashboard.kpis.week_over_week_delta;
  const deltaStr = delta >= 0 ? `+${delta}%` : `${delta}%`;

  if (dashboard.kpis.total_analyses === 0) return <EmptyState />;

  return (
    <div className="flex w-full flex-col gap-5">
      {/* Page header */}
      <header>
        <p
          className="text-[11px] font-bold tracking-[.13em] uppercase"
          style={{ color: '#5446dc', marginBottom: 8 }}
        >
          Panorama general
        </p>
        <h1 className="text-[30px] leading-tight font-bold tracking-[-0.03em] text-[#15162c]">
          Dashboard
        </h1>
        <p
          className="mt-1.5 text-[14.5px] leading-snug"
          style={{ color: '#7e7f99' }}
        >
          Actividad, credibilidad y riesgos detectados en los últimos 14 días.
        </p>
      </header>

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Análisis totales"
          value={String(dashboard.kpis.total_analyses)}
          sub="este mes"
          icon={<IcList className="size-5" />}
          tint="#eeebfc"
          color="#6356e6"
          delta={{ dir: delta >= 0 ? 'up' : 'down', value: deltaStr }}
          spark={sparkTotal.length >= 2 ? sparkTotal : undefined}
          hint="Número total de análisis que has completado."
        />
        <KpiCard
          label="Tasa de fiabilidad"
          value={`${dashboard.kpis.reliable_rate}%`}
          sub="veredicto «fiable»"
          icon={<IcShield className="size-5" />}
          tint="#def4ea"
          color="#13b877"
          spark={sparkConf.length >= 2 ? sparkConf : undefined}
          hint="Porcentaje de tus análisis con veredicto «Verdadera» sobre el total completado."
        />
        <KpiCard
          label="Confianza media"
          value={`${dashboard.kpis.average_confidence}%`}
          sub="media ponderada"
          icon={<IcSparkle className="size-5" />}
          tint="#e4f1fc"
          color="#2c97e8"
          spark={sparkConf.length >= 2 ? sparkConf : undefined}
          hint="Seguridad media del modelo en sus veredictos, promediada sobre todos tus análisis."
        />
        <KpiCard
          label="Alertas activas"
          value={String(dashboard.alerts.length)}
          sub="baja credibilidad"
          icon={<IcWarn className="size-5" />}
          tint="#fbe4e8"
          color="#e0556b"
          spark={sparkTotal.length >= 2 ? sparkTotal : undefined}
          hint="Análisis recientes con puntuación de credibilidad baja que requieren atención."
        />
      </div>

      {/* Trend + Sources row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.62fr_1fr]">
        <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
                Tendencia (14 días)
              </h2>
              <p
                className="mt-1 text-[13px] leading-snug"
                style={{ color: '#7e7f99' }}
              >
                Volumen diario de análisis y confianza media del periodo.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span
                className="flex items-center gap-1.5 text-[12px] font-semibold"
                style={{ color: '#7e7f99' }}
              >
                <span
                  className="size-[13px] rounded-[4px]"
                  style={{
                    background: 'linear-gradient(180deg,#8579f0,#5e50e0)',
                  }}
                />
                Volumen
              </span>
              <span
                className="flex items-center gap-1.5 text-[12px] font-semibold"
                style={{ color: '#7e7f99' }}
              >
                <span
                  className="inline-block h-[3px] w-[18px] rounded-full"
                  style={{ background: '#5446dc' }}
                />
                Confianza
              </span>
            </div>
          </div>
          {dashboard.trend.length > 0 ? (
            <TrendChart data={dashboard.trend} />
          ) : (
            <div className="flex min-h-44 items-center justify-center">
              <p className="text-sm font-medium" style={{ color: '#7e7f99' }}>
                Sin datos de tendencia todavía.
              </p>
            </div>
          )}
        </section>

        <SourcesCard items={dashboard.source_breakdown} />
      </div>

      {/* Domains + Alerts row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1.1fr]">
        <DomainsCard items={dashboard.domain_breakdown} />
        <AlertsCard items={dashboard.alerts} />
      </div>
    </div>
  );
}
