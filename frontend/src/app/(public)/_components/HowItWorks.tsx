'use client';

import { useEffect, useRef, useState } from 'react';
import type { ReactNode, RefObject } from 'react';
import LanguageIcon from '@/assets/Language';
import Magnifier from '@/assets/Magnifier';
import MedicalCrossIcon from '@/assets/MedicalCross';
import ScanIcon from '@/assets/Scan';
import { container } from './container';

const EASE = 'ease-[cubic-bezier(0.22,0.61,0.36,1)]';
const POP = 'ease-[cubic-bezier(0.2,1.2,0.4,1)]';

/** Entrada del bloque de un paso: aparece cuando su panel entra en pantalla. */
const rv = (on: boolean, delay = '') =>
  `transition duration-700 ${EASE} ${delay} ${on ? '' : 'translate-y-6.5 opacity-0 motion-reduce:translate-y-0 motion-reduce:opacity-100'}`;

/** Rótulo de sección dentro de la consola. */
const DH = 'font-mono text-[10px] tracking-[0.12em] text-console-dim uppercase';

/** Metadato monoespaciado bajo cada fila de la consola. */
const META = 'font-mono text-[9.5px] tracking-[0.04em] text-console-meta';

/** Etiqueta de veredicto sobre fondo oscuro. */
const PILL =
  'rounded-full px-2.25 py-1 text-center font-mono text-[9.5px] font-bold tracking-[0.06em] uppercase';

/** Aparición de una fila de la consola, desplazándose desde abajo. */
const enter = (on: boolean) =>
  `transition-[opacity,transform] duration-450 ${EASE} ${on ? '' : 'translate-y-2.5 opacity-0'}`;

const CARET =
  'ml-px inline-block h-3 w-1.5 animate-caret bg-verdict-real align-[-1px] motion-reduce:animate-none';

const TYPE_TICK = 34;

/**
 * Reinicia la maqueta cada `total` ms mientras está a la vista; `null` significa que
 * no se anima (sin JS o con movimiento reducido) y se pinta directamente el estado final.
 */
function useLoop(total: number) {
  const ref = useRef<HTMLDivElement>(null);
  const [cycle, setCycle] = useState<number | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (
      !node ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    let timer: ReturnType<typeof setInterval> | undefined;
    const next = () => setCycle(n => (n ?? 0) + 1);

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && timer === undefined) {
          next();
          timer = setInterval(next, total);
        } else if (!entry.isIntersecting && timer !== undefined) {
          clearInterval(timer);
          timer = undefined;
        }
      },
      { threshold: 0.25 }
    );
    observer.observe(node);

    return () => {
      clearInterval(timer);
      observer.disconnect();
    };
  }, [total]);

  return [ref, cycle] as const;
}

/**
 * Cuántos hitos de `marks` (ms desde el inicio del ciclo) se han alcanzado ya. El avance
 * se guarda junto a su ciclo, de modo que uno nuevo vuelve a cero al renderizar y no
 * hace falta reiniciarlo desde el efecto.
 */
function useMarks(cycle: number | null, marks: readonly number[]) {
  const [state, setState] = useState({ cycle, reached: marks.length });

  useEffect(() => {
    if (cycle === null) return;

    const timers = marks.map((ms, i) =>
      setTimeout(() => setState({ cycle, reached: i + 1 }), ms)
    );

    return () => timers.forEach(clearTimeout);
  }, [cycle, marks]);

  return state.cycle === cycle ? state.reached : 0;
}

/** Longitud ya «escrita» de `text`, avanzando a ritmo constante desde que `start` es true. */
function useTyped(
  cycle: number | null,
  text: string,
  start: boolean,
  duration: number
) {
  const [state, setState] = useState({ cycle, len: text.length });

  useEffect(() => {
    if (!start) return;

    const step = Math.max(1, Math.ceil(text.length / (duration / TYPE_TICK)));
    const timer = setInterval(
      () =>
        setState(prev => ({
          cycle,
          len: Math.min(
            text.length,
            (prev.cycle === cycle ? prev.len : 0) + step
          ),
        })),
      TYPE_TICK
    );

    return () => clearInterval(timer);
  }, [cycle, text, start, duration]);

  return state.cycle === cycle ? state.len : 0;
}

/** Cuenta de 0 a `to` con desaceleración cúbica desde que `start` es true. */
function useCount(
  cycle: number | null,
  to: number,
  start: boolean,
  duration: number
) {
  const [state, setState] = useState({ cycle, value: to });

  useEffect(() => {
    if (!start) return;

    const from = performance.now();
    const timer = setInterval(() => {
      const p = Math.min(1, (performance.now() - from) / duration);
      setState({ cycle, value: Math.round(to * (1 - (1 - p) ** 3)) });
      if (p >= 1) clearInterval(timer);
    }, 40);

    return () => clearInterval(timer);
  }, [cycle, to, start, duration]);

  return state.cycle === cycle ? state.value : 0;
}

/** Carcasa oscura común a las cuatro maquetas: barra del agente, cuerpo y barra de avance. */
function Console({
  panelRef,
  icon,
  agent,
  tag,
  total,
  cycle,
  children,
}: {
  panelRef: RefObject<HTMLDivElement | null>;
  icon: ReactNode;
  agent: string;
  tag: string;
  total: number;
  cycle: number | null;
  children: ReactNode;
}) {
  return (
    <div
      ref={panelRef}
      className="overflow-hidden rounded-[20px] border border-console-line bg-ink-deep shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]"
    >
      <div className="flex items-center gap-2.25 border-b border-console-line bg-console-panel px-4 py-3.25 text-[11.5px] font-bold tracking-[0.06em] text-console-label uppercase">
        <span
          aria-hidden="true"
          className="grid size-3.75 shrink-0 place-items-center text-verdict-real"
        >
          {icon}
        </span>
        {agent}
        <span className="ml-auto rounded-full bg-white/8 px-2.5 py-1 text-[10.5px] tracking-[0.04em] text-console-tag tabular-nums">
          {tag}
        </span>
      </div>
      {children}
      <div aria-hidden="true" className="h-0.5 bg-console-line">
        <i
          key={cycle}
          style={{ animationDuration: `${total}ms` }}
          className={`block h-full w-full bg-verdict-real ${cycle === null ? '' : 'animate-console-progress'}`}
        />
      </div>
    </div>
  );
}

/* ---------------- 01 · Extractor ---------------- */

const EXTRACT_TOTAL = 13000;
const EXTRACT_DELAY = 500;
const EXTRACT_STEP = 72;

/** Texto de entrada troceado; `claim > 0` marca el segmento que alimenta una ficha. */
const extractSegments = [
  { claim: 0, text: 'Un artículo viral asegura que' },
  {
    claim: 1,
    text: 'la vitamina C en dosis altas previene el resfriado por completo.',
  },
  {
    claim: 0,
    text: 'Cita un estudio con 200 participantes en el que se observó',
  },
  { claim: 2, text: 'una reducción del 70 % de los casos' },
  { claim: 0, text: 'y añade que' },
  { claim: 3, text: 'tomar 3 g al día no supone ningún riesgo' },
  { claim: 0, text: 'para la salud.' },
];

const extractWords = extractSegments
  .flatMap(seg =>
    seg.text.split(' ').map((word, i, all) => ({
      word,
      claim: seg.claim,
      closes: seg.claim > 0 && i === all.length - 1 ? seg.claim : 0,
    }))
  )
  .map((word, i) => ({ ...word, key: `${i}-${word.word}` }));

const extractSentence = extractSegments.map(seg => seg.text).join(' ');

const extractClaims = [
  {
    id: 'C-01',
    kind: 'causal',
    text: 'Dosis altas de vitamina C previenen el resfriado por completo.',
    meta: 'cifra: null · fuente: no',
  },
  {
    id: 'C-02',
    kind: 'estadística',
    text: 'Reducción del 70 % de los casos.',
    meta: '70 % · n=200 · fuente: sí',
  },
  {
    id: 'C-03',
    kind: 'seguridad',
    text: '3 g/día no supone ningún riesgo.',
    meta: '3 g/día · fuente: no',
  },
];

/** Índice de la última palabra de cada afirmación: al alcanzarla encaja su ficha. */
const extractHits = extractClaims.map((_, i) =>
  extractWords.reduce((last, word, k) => (word.closes === i + 1 ? k : last), -1)
);

function ExtractorArt() {
  const [ref, cycle] = useLoop(EXTRACT_TOTAL);
  const [state, setState] = useState({ cycle, cursor: extractWords.length });

  useEffect(() => {
    if (cycle === null) return;

    let walk: ReturnType<typeof setInterval> | undefined;
    const kickoff = setTimeout(() => {
      walk = setInterval(
        () =>
          setState(prev => ({
            cycle,
            cursor: Math.min(
              extractWords.length,
              (prev.cycle === cycle ? prev.cursor : 0) + 1
            ),
          })),
        EXTRACT_STEP
      );
    }, EXTRACT_DELAY);

    return () => {
      clearTimeout(kickoff);
      clearInterval(walk);
    };
  }, [cycle]);

  const head = (state.cycle === cycle ? state.cursor : 0) - 1;
  const found = extractHits.filter(k => head >= k).length;

  return (
    <Console
      panelRef={ref}
      icon={<ScanIcon className="size-3.75" />}
      agent="Extractor"
      tag={
        found === 0
          ? 'parsing…'
          : `${found} ${found === 1 ? 'afirmación extraída' : 'afirmaciones extraídas'}`
      }
      total={EXTRACT_TOTAL}
      cycle={cycle}
    >
      <div className="grid gap-6 p-6 lg:grid-cols-[1fr_300px]">
        <div>
          <div className={`${DH} mb-3.5`}>Entrada · texto pegado</div>
          <p
            aria-hidden="true"
            className="font-mono text-[13.5px] leading-loose tracking-[-0.01em] text-console-dim"
          >
            {extractWords.map((word, i) => (
              <span
                key={word.key}
                className={
                  i > head
                    ? ''
                    : !word.claim
                      ? 'text-console-text'
                      : i === head
                        ? 'rounded-[3px] bg-verdict-real text-ink-deep shadow-[0_0_12px_rgba(19,184,119,0.45)]'
                        : 'rounded-[3px] bg-verdict-real/16 text-console-glow'
                }
              >
                {word.word}{' '}
              </span>
            ))}
          </p>
          <p className="sr-only">{extractSentence}</p>
        </div>

        <div className="flex flex-col gap-2.5">
          <div className={DH}>Afirmaciones</div>
          {extractClaims.map((claim, i) => (
            <div
              key={claim.id}
              className={`rounded-[11px] border border-console-edge bg-console-panel px-3.25 py-2.75 transition-[opacity,transform] duration-450 ${POP} ${found > i ? '' : 'translate-x-6.5 opacity-0'}`}
            >
              <div className="flex justify-between font-mono text-[9.5px] font-bold tracking-[0.08em] text-verdict-real">
                <span>{claim.id}</span>
                <span>{claim.kind}</span>
              </div>
              <div className="mt-1.5 text-[12.5px] leading-[1.45] font-medium text-console-bright">
                {claim.text}
              </div>
              <div className={`mt-1.75 ${META}`}>{claim.meta}</div>
            </div>
          ))}
        </div>
      </div>
    </Console>
  );
}

/* ---------------- 02 · Traductor ---------------- */

const TRANSLATE_TOTAL = 12500;
const TRANSLATE_TYPE = 1100;
const TRANSLATE_STARTS = [500, 2400, 4300];
const TRANSLATE_DONES = TRANSLATE_STARTS.map(ms => ms + TRANSLATE_TYPE);

const translations = [
  {
    from: '"la vitamina C mejora la inmunidad"',
    to: '"vitamin C boosts your immune system"',
    mesh: 'mesh: D001205 · ascorbic acid',
  },
  {
    from: '"previene el resfriado por completo"',
    to: '"prevents colds completely"',
    mesh: 'mesh: D003139 · common cold',
  },
  {
    from: '"3 g al día no supone riesgo"',
    to: '"mega-doses are safe"',
    mesh: 'mesh: Q000008 · adverse effects',
  },
];

function TranslationRow({
  cycle,
  row,
  started,
  done,
}: {
  cycle: number | null;
  row: (typeof translations)[number];
  started: boolean;
  done: boolean;
}) {
  const len = useTyped(cycle, row.to, started, TRANSLATE_TYPE);

  return (
    <div className="grid items-center gap-1.5 border-b border-console-line py-3.25 last:border-b-0 lg:grid-cols-[1fr_26px_1fr] lg:gap-3.5">
      <div
        className={`font-mono text-[12.5px] transition-colors duration-300 ${started ? 'text-console-text' : 'text-console-dim'}`}
      >
        {row.from}
      </div>
      <div
        aria-hidden="true"
        className={`font-mono text-[13px] transition-colors duration-300 lg:text-center ${started ? 'text-verdict-real' : 'text-console-edge'}`}
      >
        →
      </div>
      <div>
        <div className="min-h-4.75 font-mono text-[12.5px] text-console-glow">
          {row.to.slice(0, len)}
          {len < row.to.length && <span aria-hidden="true" className={CARET} />}
        </div>
        <span
          className={`mt-1.25 block font-mono text-[9.5px] tracking-[0.06em] text-console-meta transition-opacity duration-400 ${done ? 'opacity-100' : 'opacity-0'}`}
        >
          {row.mesh}
        </span>
      </div>
    </div>
  );
}

function TranslatorArt() {
  const [ref, cycle] = useLoop(TRANSLATE_TOTAL);
  const started = useMarks(cycle, TRANSLATE_STARTS);
  const done = useMarks(cycle, TRANSLATE_DONES);

  return (
    <Console
      panelRef={ref}
      icon={<LanguageIcon className="size-3.75" />}
      agent="Traductor"
      tag={done === 0 ? 'es → en' : `${done} / 3 normalizadas`}
      total={TRANSLATE_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>ES → EN · MeSH</div>
        {translations.map((row, i) => (
          <TranslationRow
            key={row.from}
            cycle={cycle}
            row={row}
            started={started > i}
            done={done > i}
          />
        ))}
        <div
          className={`mt-4 font-mono text-[10px] tracking-[0.06em] text-console-meta transition-opacity duration-500 ${done === translations.length ? 'opacity-100' : 'opacity-0'}`}
        >
          lenguaje detectado: es · confianza 99.87%
        </div>
      </div>
    </Console>
  );
}

/* ---------------- 03 · Investigador ---------------- */

const INVESTIGATE_TOTAL = 14000;
const INVESTIGATE_QUERY = 'ascorbic acid AND common cold AND prophylaxis';
const INVESTIGATE_TYPE = 1600;
const INVESTIGATE_START = [300];
const INVESTIGATE_DBS = [2100, 2400, 2700, 3000];
const INVESTIGATE_LOGS = [3400, 4400];
const INVESTIGATE_SRCS = [5000, 5800, 6600];

const databases = [
  { name: 'pubmed', hits: 128 },
  { name: 'cochrane', hits: 7 },
  { name: 'nih.ods', hits: 3 },
  { name: 'efsa', hits: 2 },
];

const investigateLog = [
  <>
    filter: systematic_review, rct · lang: en · 2015-2025 →{' '}
    <b className="font-medium text-console-text">12</b>
  </>,
  <>
    rank: relevance × evidence_grade →{' '}
    <b className="font-medium text-console-text">3 fuentes</b>
  </>,
];

const investigateSources = [
  {
    name: 'Revisión sistemática · profilaxis con vitamina C',
    meta: 'cochrane/2023 · n=11306 · doi:10.1002/14651858 · rank 0.94',
    stance: 'contradice',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
  {
    name: 'Ficha de micronutrientes · ácido ascórbico',
    meta: 'nih.ods/2024 · fact sheet · rank 0.88',
    stance: 'respalda',
    tone: 'bg-verdict-real/16 text-verdict-real-on-dark',
  },
  {
    name: 'Límite superior tolerable de ingesta',
    meta: 'efsa/2022 · nutrition panel · UL 2 g/día · rank 0.81',
    stance: 'no concluyente',
    tone: 'bg-verdict-uncertain/16 text-verdict-uncertain-on-dark',
  },
];

function InvestigatorArt() {
  const [ref, cycle] = useLoop(INVESTIGATE_TOTAL);
  const querying = useMarks(cycle, INVESTIGATE_START);
  const hits = useMarks(cycle, INVESTIGATE_DBS);
  const logs = useMarks(cycle, INVESTIGATE_LOGS);
  const found = useMarks(cycle, INVESTIGATE_SRCS);
  const len = useTyped(
    cycle,
    INVESTIGATE_QUERY,
    querying > 0,
    INVESTIGATE_TYPE
  );

  return (
    <Console
      panelRef={ref}
      icon={<Magnifier className="size-3.75" />}
      agent="Investigador"
      tag={found === 0 ? 'query…' : `${found} / 3 fuentes · 12 estudios`}
      total={INVESTIGATE_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>ES→EN normalizado · 4 bases</div>

        <div className="flex items-center gap-2.75 rounded-xl border border-console-edge bg-console-panel px-3.5 py-2.75">
          <span
            aria-hidden="true"
            className="size-3.5 shrink-0 animate-spin rounded-full border-[1.8px] border-verdict-real border-r-transparent motion-reduce:animate-none"
          />
          <span className="min-h-4.5 font-mono text-xs text-console-bright">
            {INVESTIGATE_QUERY.slice(0, len)}
            {len < INVESTIGATE_QUERY.length && (
              <span aria-hidden="true" className={CARET} />
            )}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.75">
          {databases.map((db, i) => (
            <span
              key={db.name}
              className={`rounded-full border px-2.75 py-1.25 font-mono text-[10px] tracking-[0.04em] transition duration-350 ${hits > i ? 'border-verdict-real/50 bg-verdict-real/12 text-console-mint' : 'border-console-edge text-console-dim'}`}
            >
              {db.name}
              <em
                className={`ml-1.5 text-verdict-real not-italic transition-opacity duration-300 ${hits > i ? 'opacity-100' : 'opacity-0'}`}
              >
                {db.hits}
              </em>
            </span>
          ))}
        </div>

        <div className="mt-3.5 min-h-4.75 font-mono text-xs leading-[1.9] text-console-dim">
          {logs > 0 &&
            investigateLog[Math.min(logs, investigateLog.length) - 1]}
        </div>

        <div className="mt-2 flex flex-col">
          {investigateSources.map((source, i) => (
            <div
              key={source.name}
              className={`grid items-center gap-2 border-t border-console-line py-3.5 ${enter(found > i)} lg:grid-cols-[1fr_auto] lg:gap-3.5`}
            >
              <span className="text-[13px] leading-[1.4] font-medium text-console-bright">
                {source.name}
                <span className={`mt-1.25 block font-normal ${META}`}>
                  {source.meta}
                </span>
              </span>
              <span
                className={`${PILL} justify-self-start whitespace-nowrap ${source.tone}`}
              >
                {source.stance}
              </span>
            </div>
          ))}
        </div>

        <div
          className={`mt-4.5 transition-opacity duration-500 ${found === investigateSources.length ? 'opacity-100' : 'opacity-0'}`}
        >
          <small className="font-mono text-[9.5px] tracking-[0.07em] text-console-meta uppercase">
            cobertura de evidencia · 3/3 afirmaciones con evidencia científica
          </small>
        </div>
      </div>
    </Console>
  );
}

/* ---------------- 04 · Experto en salud ---------------- */

const EXPERT_TOTAL = 14000;
const EXPERT_SCORE = 41;
const EXPERT_COUNT = 1300;
const EXPERT_ROWS = [500, 1400, 2300];
const EXPERT_CALC = [3200, 4600];

const judgements = [
  {
    id: 'C-01',
    text: 'Previene el resfriado por completo',
    basis: 'guía OMS · revisión cochrane 2023',
    verdict: 'refutada',
    weight: '−18',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
  {
    id: 'C-02',
    text: 'Reducción del 70 % de los casos',
    basis: 'dato real, extrapolación indebida',
    verdict: 'con matices',
    weight: '+9',
    tone: 'bg-verdict-uncertain/16 text-verdict-uncertain-on-dark',
  },
  {
    id: 'C-03',
    text: '3 g/día no supone ningún riesgo',
    basis: 'EFSA · UL 2 g/día',
    verdict: 'refutada',
    weight: '−14',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
];

function HealthExpertArt() {
  const [ref, cycle] = useLoop(EXPERT_TOTAL);
  const judged = useMarks(cycle, EXPERT_ROWS);
  const calc = useMarks(cycle, EXPERT_CALC);
  const score = useCount(cycle, EXPERT_SCORE, calc > 0, EXPERT_COUNT);

  return (
    <Console
      panelRef={ref}
      icon={<MedicalCrossIcon className="size-3.75" />}
      agent="Experto en salud"
      tag={
        calc > 1
          ? `${EXPERT_SCORE} / 100 · falso`
          : judged === 0
            ? 'scoring…'
            : `${judged} / 3 juzgadas`
      }
      total={EXPERT_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>
          pubmed · consenso OMS · cochrane · efsa · nih
        </div>

        {judgements.map((row, i) => (
          <div
            key={row.id}
            className={`grid grid-cols-[52px_1fr] items-center gap-x-3 gap-y-2 border-t border-console-line py-3 ${enter(judged > i)} lg:grid-cols-[52px_1fr_92px_82px] lg:gap-y-0`}
          >
            <span className="col-start-1 row-start-1 font-mono text-[10px] font-bold tracking-[0.06em] text-verdict-real">
              {row.id}
            </span>
            <span className="col-start-2 row-start-1 text-[12.5px] leading-[1.4] text-console-bright">
              {row.text}
              <em className={`mt-1 block not-italic ${META}`}>{row.basis}</em>
            </span>
            <span
              className={`${PILL} col-start-2 row-start-2 justify-self-start lg:col-start-3 lg:row-start-1 lg:justify-self-stretch ${row.tone}`}
            >
              {row.verdict}
            </span>
            <span className="col-start-2 row-start-2 justify-self-end text-right font-mono text-[11px] text-console-mint tabular-nums lg:col-start-4 lg:row-start-1">
              {row.weight}
            </span>
          </div>
        ))}

        <div
          className={`grid items-center gap-3.5 border-t border-console-line pt-4.5 transition-opacity duration-500 lg:grid-cols-[1fr_auto] lg:gap-4.5 ${calc > 0 ? 'opacity-100' : 'opacity-0'}`}
        >
          <div className="font-mono text-[11px] leading-[1.8] text-console-meta">
            base <b className="font-medium text-console-text">64</b> ·
            ponderación por gravedad clínica
            <br />
            −18 +9 −14 ={' '}
            <b className="font-medium text-console-text">{EXPERT_SCORE}</b>
          </div>
          <div className="lg:text-right">
            <div className="font-mono text-[42px] leading-none font-bold tracking-[-0.02em] text-verdict-fake-on-dark tabular-nums">
              {score}
              <small className="text-sm font-medium text-console-meta">
                /100
              </small>
            </div>
            <span className="mt-2 inline-block rounded-full bg-verdict-fake/16 px-2.5 py-1 font-mono text-[9.5px] font-bold tracking-[0.08em] text-verdict-fake-on-dark uppercase">
              falso · credibilidad baja
            </span>
          </div>
        </div>
      </div>
    </Console>
  );
}

/* ---------------- sección ---------------- */

const steps = [
  {
    n: '01',
    title: 'Extractor de información',
    body: 'Lee el contenido y aísla cada afirmación médica, las cifras y las fuentes citadas, sin perder el contexto.',
    Art: ExtractorArt,
  },
  {
    n: '02',
    title: 'Traductor',
    body: 'Normaliza el idioma y estandariza la terminología clínica para que cada afirmación se contraste sobre una base común.',
    Art: TranslatorArt,
  },
  {
    n: '03',
    title: 'Investigador',
    body: 'Busca evidencia científica en la literatura biomédica y reúne las fuentes que respaldan o contradicen cada afirmación.',
    Art: InvestigatorArt,
  },
  {
    n: '04',
    title: 'Experto en salud',
    body: 'Contrasta cada afirmación con el consenso médico y las fuentes de referencia, y calcula la puntuación de credibilidad.',
    Art: HealthExpertArt,
  },
];

export default function HowItWorks() {
  const panels = useRef<(HTMLElement | null)[]>([]);
  const [revealed, setRevealed] = useState(() => steps.map(() => false));
  const [active, setActive] = useState(0);

  useEffect(() => {
    const nodes = panels.current.filter(node => node !== null);
    const ratios = steps.map(() => 0);

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          ratios[nodes.indexOf(entry.target as HTMLElement)] =
            entry.intersectionRatio;
        }
        setActive(ratios.indexOf(Math.max(...ratios)));
        setRevealed(prev => prev.map((on, i) => on || ratios[i] > 0.25));
      },
      { threshold: [0, 0.25, 0.5, 0.75, 1] }
    );
    nodes.forEach(node => observer.observe(node));

    return () => observer.disconnect();
  }, []);

  return (
    <section id="como-funciona" aria-labelledby="how-title" className="pb-10">
      <div
        className={`${container} grid items-start gap-6 lg:grid-cols-[0.82fr_1.18fr] lg:gap-16`}
      >
        <aside className="flex flex-col justify-center pt-15 lg:sticky lg:top-18 lg:h-[calc(100vh-72px)] lg:pt-24 lg:pb-10">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Cómo funciona
          </span>
          <h2
            id="how-title"
            className="my-4 font-display text-[34px] leading-[1.1] font-normal tracking-[-0.005em] text-ink md:text-[46px]"
          >
            Agentes especializados,
            <br />
            un veredicto fiable
          </h2>
          <p className="max-w-105 text-[16.5px] leading-[1.65] text-muted">
            Cada afirmación pasa por una cadena de especialistas de IA que se
            complementan, y verás exactamente qué aportó cada uno.
          </p>
          <div
            aria-hidden="true"
            className="mt-9.5 flex flex-col gap-0.5 border-l-2 border-line"
          >
            {steps.map((step, i) => (
              <div
                key={step.n}
                className={`relative flex items-center gap-3.5 py-2 pl-5.5 before:absolute before:top-1.5 before:bottom-1.5 before:-left-0.5 before:w-0.5 before:origin-top before:rounded-sm before:bg-primary before:transition before:duration-350 before:content-[''] ${active === i ? '' : 'before:scale-y-30 before:opacity-0'}`}
              >
                <span
                  className={`grid size-7 shrink-0 place-items-center rounded-full border-[1.5px] text-[11.5px] font-bold transition duration-300 ${active === i ? 'border-primary bg-primary text-white' : 'border-line-strong bg-white text-faint'}`}
                >
                  {step.n}
                </span>
                <span
                  className={`text-[15px] font-semibold transition-colors duration-300 ${active === i ? 'text-ink' : 'text-faint'}`}
                >
                  {step.title}
                </span>
              </div>
            ))}
          </div>
        </aside>

        <div>
          {steps.map((step, i) => (
            <article
              key={step.n}
              ref={node => {
                panels.current[i] = node;
              }}
              className="flex flex-col justify-center py-10 lg:min-h-screen lg:py-20"
            >
              <div className={rv(revealed[i])}>
                <div className="mb-3.5 flex items-center gap-3 text-xs font-extrabold tracking-[0.12em] text-primary uppercase">
                  <span className="h-[1.5px] w-6.5 bg-primary" />
                  Paso {step.n}
                </div>
                <h3 className="text-[27px] font-semibold tracking-[-0.01em] text-ink">
                  {step.title}
                </h3>
              </div>
              <p
                className={`${rv(revealed[i], 'delay-60')} mt-3 mb-6.5 max-w-140 text-base leading-[1.65] text-muted`}
              >
                {step.body}
              </p>
              <div className={rv(revealed[i], 'delay-140')}>
                <step.Art />
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
