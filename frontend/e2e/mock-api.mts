import { randomBytes, randomUUID } from 'node:crypto';
import { createServer, type IncomingMessage } from 'node:http';

import type { components, paths } from '../src/types/api';

type Schemas = components['schemas'];
type Analysis = Schemas['AnalysisHistoryItem'];
type Stage = NonNullable<Analysis['stage']>;
type ErrorCode = Schemas['ErrorCode'];
// Cuerpo JSON de la respuesta 200 de una operación del contrato generado.
type Ok<P extends keyof paths, M extends keyof paths[P]> = paths[P][M] extends {
  responses: { 200: { content: { 'application/json': infer T } } };
}
  ? T
  : never;

interface Row {
  analysis: Analysis;
  // Momento en que termina el pipeline simulado; null si no termina nunca.
  finishesAt: number | null;
}

interface Reply {
  status: number;
  body?: unknown;
}

interface Route {
  method: string;
  pattern: RegExp;
  public?: boolean;
  handle: (
    id: string,
    req: IncomingMessage,
    url: URL
  ) => Reply | Promise<Reply>;
}

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} must be set; see playwright.config.ts.`);
  return value;
}

const PORT = Number(requiredEnv('MOCK_API_PORT'));
const WEB_ORIGIN = requiredEnv('WEB_ORIGIN');
const PIPELINE_MS = 4000;
const STAGES: Stage[] = [
  'preparing',
  'extractor',
  'translator',
  'investigator',
  'health_expert',
];
const DAYS_BY_RANGE: Record<string, number> = { '7d': 7, '30d': 30, '90d': 90 };

const hoursAgo = (hours: number) =>
  new Date(Date.now() - hours * 3_600_000).toISOString();

// Informe con el que termina todo análisis que la prueba envía o reintenta.
const FAKE_REPORT = {
  label: 'falsa',
  confidence: 0.82,
  evidence_coverage: 1,
  verdict: 'fake',
  credibility: 18,
  confidence_level: 'medium',
  explanation:
    'La evidencia revisada no respalda que la vitamina C en dosis altas prevenga el resfriado común en la población general.',
  claims: [
    {
      text: 'La vitamina C en dosis altas previene por completo el resfriado común.',
      label: 'falsa',
      confidence: 0.82,
      verdict: 'fake',
    },
  ],
  sources: [
    {
      title: 'Vitamin C for preventing and treating the common cold',
      url: 'https://example.org/vitamin-c-common-cold',
      source: 'Europe PMC',
      year: '2013',
      statements: [
        {
          claim_index: 0,
          text: 'Regular supplementation did not reduce the incidence of colds in the general population.',
          stance: 'contradicts',
        },
      ],
    },
  ],
} satisfies Partial<Analysis>;

function analysis(
  fields: Pick<
    Analysis,
    'analysis_id' | 'source_type' | 'status' | 'created_at'
  > &
    Partial<Analysis>
): Analysis {
  return {
    origin: 'web',
    user_id: 'user_e2e',
    verdict: 'uncertain',
    credibility: null,
    confidence_level: null,
    ...fields,
  };
}

// Un análisis de cada estado y veredicto; los ids legibles sirven de URL en las pruebas.
function seed(): Map<string, Row> {
  const rows: Row[] = [
    {
      finishesAt: null,
      analysis: analysis({
        analysis_id: 'pending-investigator',
        source_type: 'text',
        status: 'pending',
        stage: 'investigator',
        created_at: hoursAgo(0.1),
        input_text: 'El ayuno intermitente cura la diabetes tipo 2.',
      }),
    },
    {
      finishesAt: null,
      analysis: analysis({
        analysis_id: 'failed-connection',
        source_type: 'text',
        status: 'failed',
        error_code: 'CONNECTION',
        created_at: hoursAgo(1),
        input_text: 'Beber agua con limón en ayunas elimina las toxinas.',
      }),
    },
    {
      finishesAt: null,
      analysis: analysis({
        analysis_id: 'done-fake',
        source_type: 'text',
        status: 'done',
        created_at: hoursAgo(2),
        completed_at: hoursAgo(1.9),
        input_text:
          'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común.',
        ...FAKE_REPORT,
      }),
    },
    {
      finishesAt: null,
      analysis: analysis({
        analysis_id: 'done-real',
        source_type: 'url',
        status: 'done',
        created_at: hoursAgo(26),
        completed_at: hoursAgo(25.9),
        input_url: 'https://www.example.org/salud/lavado-de-manos',
        label: 'verdadera',
        confidence: 0.9,
        evidence_coverage: 1,
        verdict: 'real',
        credibility: 90,
        confidence_level: 'high',
        explanation:
          'Los estudios revisados confirman que lavarse las manos reduce las infecciones respiratorias.',
        claims: [
          {
            text: 'Lavarse las manos reduce las infecciones respiratorias.',
            label: 'verdadera',
            confidence: 0.9,
            verdict: 'real',
          },
        ],
        sources: [],
      }),
    },
    {
      finishesAt: null,
      analysis: analysis({
        analysis_id: 'done-uncertain',
        source_type: 'file',
        status: 'done',
        created_at: hoursAgo(240),
        completed_at: hoursAgo(239.9),
        file_filename: 'informe-dieta.pdf',
        input_text: 'La dieta cetogénica mejora la memoria en adultos sanos.',
        label: 'incierta',
        confidence: 0.5,
        evidence_coverage: 0,
        verdict: 'uncertain',
        credibility: null,
        confidence_level: 'low',
        explanation:
          'No se encontró evidencia suficiente para confirmar ni refutar la afirmación.',
        claims: [
          {
            text: 'La dieta cetogénica mejora la memoria en adultos sanos.',
            label: 'incierta',
            confidence: 0.5,
            verdict: 'uncertain',
          },
        ],
        sources: [],
      }),
    },
  ];
  return new Map(rows.map(row => [row.analysis.analysis_id, row]));
}

let store = seed();

// Encola como el backend: created_at se reinicia y el resultado anterior se borra.
function enqueue(previous: Analysis): Row {
  return {
    finishesAt: Date.now() + PIPELINE_MS,
    analysis: analysis({
      analysis_id: previous.analysis_id,
      source_type: previous.source_type,
      status: 'pending',
      created_at: new Date().toISOString(),
      input_text: previous.input_text,
      input_url: previous.input_url,
      file_filename: previous.file_filename,
      share_token: previous.share_token,
    }),
  };
}

// Avanza el pipeline simulado según el tiempo transcurrido desde que se encoló.
function settle(row: Row): Analysis {
  if (row.analysis.status !== 'pending' || row.finishesAt === null) {
    return row.analysis;
  }
  const remaining = row.finishesAt - Date.now();
  if (remaining <= 0) {
    row.analysis = {
      ...row.analysis,
      ...FAKE_REPORT,
      status: 'done',
      stage: null,
      completed_at: new Date().toISOString(),
    };
    row.finishesAt = null;
    return row.analysis;
  }
  const progress = (PIPELINE_MS - remaining) / PIPELINE_MS;
  const index = Math.min(
    STAGES.length - 1,
    Math.floor(progress * STAGES.length)
  );
  row.analysis = { ...row.analysis, stage: STAGES[index] };
  return row.analysis;
}

const all = () => [...store.values()].map(settle);
const find = (id: string) => {
  const row = store.get(id);
  return row && settle(row);
};

function toListItem(a: Analysis): Schemas['HistoryListItem'] {
  return {
    analysis_id: a.analysis_id,
    source_type: a.source_type,
    origin: a.origin,
    input_text: a.input_text,
    input_url: a.input_url,
    label: a.label,
    confidence: a.confidence,
    evidence_coverage: a.evidence_coverage,
    status: a.status,
    error_code: a.error_code,
    created_at: a.created_at,
    file_filename: a.file_filename,
    share_token: a.share_token,
    stage: a.stage,
    verdict: a.verdict,
    credibility: a.credibility,
    confidence_level: a.confidence_level,
  };
}

function toPublicReport(a: Analysis): Schemas['PublicAnalysisReport'] {
  return {
    source_type: a.source_type,
    input_text: a.input_text,
    input_url: a.input_url,
    label: a.label,
    confidence: a.confidence,
    evidence_coverage: a.evidence_coverage,
    explanation: a.explanation,
    status: a.status,
    created_at: a.created_at,
    completed_at: a.completed_at,
    file_filename: a.file_filename,
    claims: a.claims,
    sources: a.sources,
    verdict: a.verdict,
    credibility: a.credibility,
    confidence_level: a.confidence_level,
  };
}

// Misma semántica que app/db/history_query.py: el facet es la consulta sin su filtro de veredicto.
function searchHistory(query: URLSearchParams): Ok<'/history', 'get'> {
  const filter = (name: string) => query.get(name) ?? 'all';
  const search = (query.get('search') ?? '').toLowerCase();
  const days = DAYS_BY_RANGE[filter('date_range')];
  const base = all().filter(
    a =>
      (filter('status') === 'all' || a.status === filter('status')) &&
      (filter('source_type') === 'all' ||
        a.source_type === filter('source_type')) &&
      (!search ||
        [a.input_text, a.input_url, a.file_filename].some(value =>
          value?.toLowerCase().includes(search)
        )) &&
      (!days || Date.parse(a.created_at) >= Date.now() - days * 86_400_000)
  );
  // Las filas pending y failed no tienen veredicto en la base de datos.
  const verdictOf = (a: Analysis) => (a.status === 'done' ? a.verdict : null);
  const countOf = (verdict: Analysis['verdict']) =>
    base.filter(a => verdictOf(a) === verdict).length;
  const verdict = filter('verdict');
  const matching =
    verdict === 'all' ? base : base.filter(a => verdictOf(a) === verdict);

  const byDate = (a: Analysis, b: Analysis) =>
    Date.parse(b.created_at) - Date.parse(a.created_at);
  const byCredibility = (a: Analysis, b: Analysis) =>
    (b.credibility ?? -1) - (a.credibility ?? -1);
  const comparators: Record<string, (a: Analysis, b: Analysis) => number> = {
    recent: byDate,
    oldest: (a, b) => byDate(b, a),
    credibility_high: byCredibility,
    credibility_low: (a, b) => byCredibility(b, a),
  };
  const sorted = [...matching].sort(
    comparators[query.get('sort') ?? 'recent'] ?? byDate
  );

  const page = Number(query.get('page') ?? 1);
  const pageSize = Number(query.get('page_size') ?? 10);
  return {
    status: 'success',
    items: sorted.slice((page - 1) * pageSize, page * pageSize).map(toListItem),
    count: matching.length,
    page,
    page_size: pageSize,
    verdict_counts: {
      total: base.length,
      real: countOf('real'),
      fake: countOf('fake'),
      mixed: countOf('mixed'),
      uncertain: countOf('uncertain'),
    },
  };
}

// Respuesta 200 tipada con la operación del contrato que simula.
const ok = <P extends keyof paths, M extends keyof paths[P]>(
  body: Ok<P, M>
): Reply => ({ status: 200, body });

const fail = (status: number, code: ErrorCode): Reply => ({
  status,
  body: {
    detail: { code, message: `Error simulado: ${code}` },
  } satisfies Schemas['ErrorResponse'],
});

async function readJson<T>(req: IncomingMessage): Promise<T> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as T;
}

const ROUTES: Route[] = [
  {
    method: 'POST',
    pattern: /^\/__reset$/,
    public: true,
    handle: () => {
      store = seed();
      return { status: 204 };
    },
  },
  {
    method: 'GET',
    pattern: /^\/config$/,
    public: true,
    handle: () =>
      ok<'/config', 'get'>({
        max_file_bytes: 10 * 1024 * 1024,
        allowed_file_suffixes: ['.md', '.pdf', '.txt'],
        min_input_text_length: 10,
        max_input_text_length: 10_000,
      }),
  },
  {
    method: 'POST',
    pattern: /^\/analysis$/,
    handle: async (_id, req) => {
      const request = await readJson<Schemas['AnalysisRequest']>(req);
      const id = randomUUID();
      store.set(
        id,
        enqueue(
          analysis({
            analysis_id: id,
            source_type: request.source_type,
            status: 'pending',
            created_at: new Date().toISOString(),
            input_text: request.text ?? null,
            input_url: request.url ?? null,
          })
        )
      );
      return ok<'/analysis', 'post'>({ status: 'pending', analysis_id: id });
    },
  },
  {
    method: 'GET',
    pattern: /^\/analysis\/([^/]+)$/,
    handle: id => {
      const found = find(id);
      if (!found) return fail(404, 'ANALYSIS_NOT_FOUND');
      return ok<'/analysis/{analysis_id}', 'get'>(found);
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/analysis\/([^/]+)$/,
    handle: id => {
      if (!store.delete(id)) return fail(404, 'ANALYSIS_NOT_FOUND');
      return ok<'/analysis/{analysis_id}', 'delete'>({
        status: 'deleted',
        analysis_id: id,
      });
    },
  },
  {
    method: 'GET',
    pattern: /^\/analysis\/([^/]+)\/status$/,
    handle: id => {
      const found = find(id);
      if (!found) return fail(404, 'ANALYSIS_NOT_FOUND');
      return ok<'/analysis/{analysis_id}/status', 'get'>({
        status: found.status,
        stage: found.stage,
      });
    },
  },
  {
    method: 'POST',
    pattern: /^\/analysis\/([^/]+)\/retry$/,
    handle: id => {
      const found = find(id);
      if (!found) return fail(404, 'ANALYSIS_NOT_FOUND');
      if (found.status !== 'failed') return fail(409, 'ANALYSIS_NOT_RETRYABLE');
      store.set(id, enqueue(found));
      return ok<'/analysis/{analysis_id}/retry', 'post'>({
        status: 'pending',
        analysis_id: id,
      });
    },
  },
  {
    method: 'POST',
    pattern: /^\/analysis\/([^/]+)\/share$/,
    handle: id => {
      const found = find(id);
      if (!found) return fail(404, 'ANALYSIS_NOT_FOUND');
      if (found.status !== 'done') return fail(409, 'ANALYSIS_NOT_SHAREABLE');
      found.share_token ??= randomBytes(32).toString('base64url');
      return ok<'/analysis/{analysis_id}/share', 'post'>({
        status: 'shared',
        share_token: found.share_token,
      });
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/analysis\/([^/]+)\/share$/,
    handle: id => {
      const found = find(id);
      if (!found) return fail(404, 'ANALYSIS_NOT_FOUND');
      found.share_token = null;
      return ok<'/analysis/{analysis_id}/share', 'delete'>({
        status: 'unshared',
        analysis_id: id,
      });
    },
  },
  {
    method: 'GET',
    pattern: /^\/history$/,
    handle: (_id, _req, url) =>
      ok<'/history', 'get'>(searchHistory(url.searchParams)),
  },
  {
    method: 'DELETE',
    pattern: /^\/history$/,
    handle: () => {
      const deleted = store.size;
      store.clear();
      return ok<'/history', 'delete'>({
        status: 'deleted',
        deleted_count: deleted,
      });
    },
  },
  {
    method: 'GET',
    pattern: /^\/history\/pending$/,
    handle: () => {
      const pending = all()
        .filter(a => a.status === 'pending')
        .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
      return ok<'/history/pending', 'get'>({
        count: pending.length,
        newest_analysis_id: pending[0]?.analysis_id ?? null,
      });
    },
  },
  {
    method: 'GET',
    pattern: /^\/shared\/([^/]+)$/,
    public: true,
    handle: token => {
      const found = all().find(
        a => a.share_token === token && a.status === 'done'
      );
      if (!found) return fail(404, 'SHARED_REPORT_NOT_FOUND');
      return ok<'/shared/{token}', 'get'>(toPublicReport(found));
    },
  },
  {
    method: 'POST',
    pattern: /^\/contact$/,
    public: true,
    handle: () => ok<'/contact', 'post'>({ status: 'sent' }),
  },
];

async function dispatch(req: IncomingMessage, url: URL): Promise<Reply> {
  for (const route of ROUTES) {
    const match = route.pattern.exec(url.pathname);
    if (!match || route.method !== req.method) continue;
    if (!route.public && !req.headers.authorization?.startsWith('Bearer ')) {
      return fail(401, 'UNAUTHENTICATED');
    }
    return route.handle(decodeURIComponent(match[1] ?? ''), req, url);
  }
  console.warn(`[mock-api] Ruta sin simular: ${req.method} ${url.pathname}`);
  return fail(501, 'INTERNAL');
}

createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', WEB_ORIGIN);
  res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  if (req.method === 'OPTIONS') {
    res.writeHead(204).end();
    return;
  }
  const reply = await dispatch(
    req,
    new URL(req.url ?? '/', `http://localhost:${PORT}`)
  );
  if (reply.body === undefined) {
    res.writeHead(reply.status).end();
    return;
  }
  res
    .writeHead(reply.status, { 'Content-Type': 'application/json' })
    .end(JSON.stringify(reply.body));
}).listen(PORT, () => {
  console.log(`[mock-api] Escuchando en http://localhost:${PORT}`);
});
