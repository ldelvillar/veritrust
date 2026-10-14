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
const DH = 'font-mono text-2xs tracking-[0.12em] text-console-dim uppercase';

/** Metadato monoespaciado bajo cada fila de la consola. */
const META = 'font-mono text-2xs tracking-[0.04em] text-console-meta';

/** Etiqueta de veredicto sobre fondo oscuro. */
const PILL =
  'rounded-full px-2.25 py-1 text-center font-mono text-2xs font-bold tracking-[0.06em] uppercase';

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
      className="overflow-hidden rounded-2xl border border-console-line bg-ink-deep shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]"
    >
      <div className="flex items-center gap-2.25 border-b border-console-line bg-console-panel px-4 py-3.25 text-2xs font-bold tracking-[0.06em] text-console-label uppercase">
        <span
          aria-hidden="true"
          className="grid size-3.75 shrink-0 place-items-center text-verdict-real"
        >
          {icon}
        </span>
        {agent}
        <span className="ml-auto rounded-full bg-white/8 px-2.5 py-1 text-2xs tracking-[0.04em] text-console-tag tabular-nums">
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

/** Texto del análisis de /ejemplo troceado; `claim > 0` marca el segmento que alimenta una ficha. */
const extractSegments = [
  {
    claim: 1,
    text: 'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común',
  },
  { claim: 0, text: 'y' },
  { claim: 2, text: 'refuerza el sistema inmunitario sin ningún riesgo,' },
  { claim: 0, text: 'según un estudio reciente.' },
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
    text: 'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
    query: 'vitamin C AND (common cold OR cold prevention) AND high dose',
  },
  {
    id: 'C-02',
    text: 'El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo.',
    query: 'vitamin C AND immune system AND high dose AND safety',
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
            className="font-mono text-sm leading-loose tracking-[-0.01em] text-console-dim"
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
                        ? 'rounded-xs bg-verdict-real text-ink-deep shadow-[0_0_12px_rgba(19,184,119,0.45)]'
                        : 'rounded-xs bg-verdict-real/16 text-console-glow'
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
              className={`rounded-xl border border-console-edge bg-console-panel px-3.25 py-2.75 transition-[opacity,transform] duration-450 ${POP} ${found > i ? '' : 'translate-x-6.5 opacity-0'}`}
            >
              <div className="font-mono text-2xs font-bold tracking-[0.08em] text-verdict-real">
                {claim.id}
              </div>
              <div className="mt-1.5 text-xs leading-[1.45] font-medium text-console-bright">
                {claim.text}
              </div>
              <div className={`mt-1.75 ${META}`}>consulta: {claim.query}</div>
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
const TRANSLATE_STARTS = [500, 2400];
const TRANSLATE_DONES = TRANSLATE_STARTS.map(ms => ms + TRANSLATE_TYPE);

const translations = [
  {
    id: 'C-01',
    from: '"El consumo diario de vitamina C en dosis altas previene por completo el resfriado común."',
    to: '"Daily consumption of high doses of vitamin C completely prevents the common cold."',
  },
  {
    id: 'C-02',
    from: '"El consumo diario de vitamina C en dosis altas refuerza el sistema inmunitario sin ningún riesgo."',
    to: '"Daily consumption of high doses of vitamin C strengthens the immune system with no risk at all."',
  },
];

function TranslationRow({
  cycle,
  row,
  started,
}: {
  cycle: number | null;
  row: (typeof translations)[number];
  started: boolean;
}) {
  const len = useTyped(cycle, row.to, started, TRANSLATE_TYPE);

  return (
    <div className="grid items-center gap-1.5 border-b border-console-line py-3.25 last:border-b-0 lg:grid-cols-[1fr_26px_1fr] lg:gap-3.5">
      <div
        className={`font-mono text-xs transition-colors duration-300 ${started ? 'text-console-text' : 'text-console-dim'}`}
      >
        {row.from}
      </div>
      <div
        aria-hidden="true"
        className={`font-mono text-sm transition-colors duration-300 lg:text-center ${started ? 'text-verdict-real' : 'text-console-edge'}`}
      >
        →
      </div>
      <div>
        <div className="min-h-4.75 font-mono text-xs text-console-glow">
          {row.to.slice(0, len)}
          {len < row.to.length && <span aria-hidden="true" className={CARET} />}
        </div>
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
      tag={done === 0 ? 'es → en' : `${done} / 2 traducidas`}
      total={TRANSLATE_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>
          ES → EN · sin corregir la afirmación
        </div>
        {translations.map((row, i) => (
          <TranslationRow
            key={row.id}
            cycle={cycle}
            row={row}
            started={started > i}
          />
        ))}
        <div
          className={`mt-4 font-mono text-2xs tracking-[0.06em] text-console-meta transition-opacity duration-500 ${done === translations.length ? 'opacity-100' : 'opacity-0'}`}
        >
          el juez compara cada fuente con la versión en inglés
        </div>
      </div>
    </Console>
  );
}

/* ---------------- 03 · Investigador ---------------- */

const INVESTIGATE_TOTAL = 14000;
const INVESTIGATE_TYPE = 1000;
const INVESTIGATE_STARTS = [300, 1500];
const INVESTIGATE_DBS = [2900, 3200, 3500];
const INVESTIGATE_LOGS = [3900, 4900];
const INVESTIGATE_SRCS = [5500, 6200, 6900, 7600];

// CIMA solo se consulta cuando la afirmación nombra un fármaco, y estas no lo hacen.
const databases = [
  { name: 'europepmc', hits: 6 },
  { name: 'pubmed', hits: 6 },
  { name: 'openfda', hits: 4 },
];

const investigateLog = [
  <>
    2 consultas · 3 bases →{' '}
    <b className="font-medium text-console-text">16 resultados</b>
  </>,
  <>
    el juez descarta 12 de otro tema →{' '}
    <b className="font-medium text-console-text">4 fuentes</b>
  </>,
];

const investigateSources = [
  {
    name: 'The Long History of Vitamin C',
    meta: 'C-01 · pubmed · frontiers in immunology · 2020',
    stance: 'contradice',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
  {
    name: 'Vitamin C in the Prevention and Treatment of the Common Cold',
    meta: 'C-01 · pubmed · american journal of lifestyle medicine · 2016',
    stance: 'no concluyente',
    tone: 'bg-verdict-uncertain/16 text-verdict-uncertain-on-dark',
  },
  {
    name: 'Vitamin C-Beyond Deficiency',
    meta: 'C-02 · europepmc · nutrients · 2026',
    stance: 'contradice',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
  {
    name: 'High-Dose Intravenous Vitamin C in Critical Illness',
    meta: 'C-02 · europepmc · medical sciences · 2026',
    stance: 'contradice',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
];

function QueryLine({
  cycle,
  id,
  query,
  started,
}: {
  cycle: number | null;
  id: string;
  query: string;
  started: boolean;
}) {
  const len = useTyped(cycle, query, started, INVESTIGATE_TYPE);

  return (
    <div className="flex items-start gap-2.75">
      <span className="pt-px font-mono text-2xs font-bold tracking-[0.06em] text-verdict-real">
        {id}
      </span>
      <span className="min-h-4.5 font-mono text-xs text-console-bright">
        {query.slice(0, len)}
        {started && len < query.length && (
          <span aria-hidden="true" className={CARET} />
        )}
      </span>
    </div>
  );
}

function InvestigatorArt() {
  const [ref, cycle] = useLoop(INVESTIGATE_TOTAL);
  const querying = useMarks(cycle, INVESTIGATE_STARTS);
  const hits = useMarks(cycle, INVESTIGATE_DBS);
  const logs = useMarks(cycle, INVESTIGATE_LOGS);
  const found = useMarks(cycle, INVESTIGATE_SRCS);

  return (
    <Console
      panelRef={ref}
      icon={<Magnifier className="size-3.75" />}
      agent="Investigador"
      tag={found === 0 ? 'query…' : `${found} / 4 fuentes · 16 resultados`}
      total={INVESTIGATE_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>Consultas del extractor · 3 bases</div>

        <div className="flex items-start gap-2.75 rounded-xl border border-console-edge bg-console-panel px-3.5 py-2.75">
          <span
            aria-hidden="true"
            className="mt-0.5 size-3.5 shrink-0 animate-spin rounded-full border-[1.8px] border-verdict-real border-r-transparent motion-reduce:animate-none"
          />
          <div className="flex flex-col gap-1.5">
            {extractClaims.map((claim, i) => (
              <QueryLine
                key={claim.id}
                cycle={cycle}
                id={claim.id}
                query={claim.query}
                started={querying > i}
              />
            ))}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.75">
          {databases.map((db, i) => (
            <span
              key={db.name}
              className={`rounded-full border px-2.75 py-1.25 font-mono text-2xs tracking-[0.04em] transition duration-350 ${hits > i ? 'border-verdict-real/50 bg-verdict-real/12 text-console-mint' : 'border-console-edge text-console-dim'}`}
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
              <span className="text-sm leading-[1.4] font-medium text-console-bright">
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
          <small className="font-mono text-2xs tracking-[0.07em] text-console-meta uppercase">
            cobertura de evidencia · 2/2 afirmaciones con evidencia científica
          </small>
        </div>
      </div>
    </Console>
  );
}

/* ---------------- 04 · Experto en salud ---------------- */

const EXPERT_TOTAL = 14000;
const EXPERT_SCORE = 29;
const EXPERT_COUNT = 1300;
const EXPERT_ROWS = [500, 1400];
const EXPERT_CALC = [2300, 3700];
const EXPERT_WRITE = [4300];
const EXPERT_TYPE = 2600;

// Probabilidad de falsedad = (contradicen + 1) / (respaldan + contradicen + 2), como en decide().
const judgements = [
  {
    id: 'C-01',
    text: 'Previene por completo el resfriado común',
    basis: '0 respaldan · 1 contradice · 1 no concluyente',
    verdict: 'falso',
    weight: '67 %',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
  {
    id: 'C-02',
    text: 'Refuerza el sistema inmunitario sin ningún riesgo',
    basis: '0 respaldan · 2 contradicen',
    verdict: 'falso',
    weight: '75 %',
    tone: 'bg-verdict-fake/16 text-verdict-fake-on-dark',
  },
];

const EXPERT_EXCERPT =
  'No hay evidencia que respalde que la vitamina C en dosis altas prevenga el resfriado común de manera absoluta.';

function HealthExpertArt() {
  const [ref, cycle] = useLoop(EXPERT_TOTAL);
  const judged = useMarks(cycle, EXPERT_ROWS);
  const calc = useMarks(cycle, EXPERT_CALC);
  const writing = useMarks(cycle, EXPERT_WRITE);
  const score = useCount(cycle, EXPERT_SCORE, calc > 0, EXPERT_COUNT);
  const len = useTyped(cycle, EXPERT_EXCERPT, writing > 0, EXPERT_TYPE);

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
            : `${judged} / 2 decididas`
      }
      total={EXPERT_TOTAL}
      cycle={cycle}
    >
      <div className="p-6">
        <div className={`${DH} mb-3.5`}>
          regla fija · probabilidad de que sea falsa
        </div>

        {judgements.map((row, i) => (
          <div
            key={row.id}
            className={`grid grid-cols-[52px_1fr] items-center gap-x-3 gap-y-2 border-t border-console-line py-3 ${enter(judged > i)} lg:grid-cols-[52px_1fr_92px_82px] lg:gap-y-0`}
          >
            <span className="col-start-1 row-start-1 font-mono text-2xs font-bold tracking-[0.06em] text-verdict-real">
              {row.id}
            </span>
            <span className="col-start-2 row-start-1 text-xs leading-[1.4] text-console-bright">
              {row.text}
              <em className={`mt-1 block not-italic ${META}`}>{row.basis}</em>
            </span>
            <span
              className={`${PILL} col-start-2 row-start-2 justify-self-start lg:col-start-3 lg:row-start-1 lg:justify-self-stretch ${row.tone}`}
            >
              {row.verdict}
            </span>
            <span className="col-start-2 row-start-2 justify-self-end text-right font-mono text-2xs text-console-mint tabular-nums lg:col-start-4 lg:row-start-1">
              {row.weight}
            </span>
          </div>
        ))}

        <div
          className={`grid items-center gap-3.5 border-t border-console-line pt-4.5 transition-opacity duration-500 lg:grid-cols-[1fr_auto] lg:gap-4.5 ${calc > 0 ? 'opacity-100' : 'opacity-0'}`}
        >
          <div className="font-mono text-2xs leading-[1.8] text-console-meta">
            media (67 + 75) / 2 ={' '}
            <b className="font-medium text-console-text">71 % falsa</b>
            <br />
            credibilidad 100 − 71 ={' '}
            <b className="font-medium text-console-text">{EXPERT_SCORE}</b>
          </div>
          <div className="lg:text-right">
            <div className="font-mono text-4xl leading-none font-bold tracking-[-0.02em] text-verdict-fake-on-dark tabular-nums">
              {score}
              <small className="text-sm font-medium text-console-meta">
                /100
              </small>
            </div>
            <span className="mt-2 inline-block rounded-full bg-verdict-fake/16 px-2.5 py-1 font-mono text-2xs font-bold tracking-[0.08em] text-verdict-fake-on-dark uppercase">
              falso · credibilidad baja
            </span>
          </div>
        </div>

        <div
          className={`mt-4.5 border-t border-console-line pt-4.5 transition-opacity duration-500 ${writing > 0 ? 'opacity-100' : 'opacity-0'}`}
        >
          <div className={`${DH} mb-2.5`}>Informe · extracto</div>
          <p className="min-h-10 text-xs leading-[1.6] text-console-bright">
            {EXPERT_EXCERPT.slice(0, len)}
            {writing > 0 && len < EXPERT_EXCERPT.length && (
              <span aria-hidden="true" className={CARET} />
            )}
          </p>
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
    body: 'Lee el contenido, aísla cada afirmación médica como una frase completa y escribe en inglés la consulta con la que se buscará.',
    Art: ExtractorArt,
  },
  {
    n: '02',
    title: 'Traductor',
    body: 'Traduce cada afirmación al inglés tal como está escrita, sin corregirla, porque casi toda la literatura biomédica está en inglés.',
    Art: TranslatorArt,
  },
  {
    n: '03',
    title: 'Investigador',
    body: 'Busca cada afirmación en PubMed, Europe PMC y openFDA (y en CIMA si nombra un fármaco). Un juez descarta los resultados que tratan de otro tema y anota si cada fuente respalda o contradice la afirmación.',
    Art: InvestigatorArt,
  },
  {
    n: '04',
    title: 'Experto en salud',
    body: 'Una regla fija convierte las posturas de las fuentes en el veredicto y la puntuación. El experto en salud explica cada veredicto con lo que dicen los resúmenes de las fuentes.',
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
          <span className="text-sm font-extrabold tracking-[0.12em] text-primary uppercase">
            Cómo funciona
          </span>
          <h2
            id="how-title"
            className="my-4 font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md"
          >
            Agentes especializados,
            <br />
            un veredicto fiable
          </h2>
          <p className="max-w-105 text-base leading-[1.65] text-muted">
            Cada afirmación pasa por cuatro pasos. Así se analizó el texto sobre
            la vitamina C del ejemplo.
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
                  className={`grid size-7 shrink-0 place-items-center rounded-full border-[1.5px] text-2xs font-bold transition duration-300 ${active === i ? 'border-primary bg-primary text-white' : 'border-line-strong bg-white text-faint'}`}
                >
                  {step.n}
                </span>
                <span
                  className={`text-base font-semibold transition-colors duration-300 ${active === i ? 'text-ink' : 'text-faint'}`}
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
                <h3 className="text-2xl font-semibold tracking-[-0.01em] text-ink">
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
