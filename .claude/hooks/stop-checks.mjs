// Stop hook: runs CI's fast checks on the files the branch changed and keeps Claude working while they fail.
import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const MAX_BLOCKS = 3;
const OUTPUT_TAIL_LINES = 40;
const root = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const stateFile = join(root, '.claude', 'hooks', '.stop-checks.json');

// CI's Claude jobs review rather than change code, and their runners lack uv and pnpm.
if (process.env.GITHUB_ACTIONS) process.exit(0);

const input = JSON.parse(readFileSync(0, 'utf8'));

const git = (...args) =>
  execFileSync('git', args, {
    cwd: root,
    encoding: 'utf8',
    maxBuffer: 1 << 28,
    stdio: ['ignore', 'pipe', 'ignore'],
  });

// The code paths of CI's backend_app, backend_evaluation and frontend filters, as git pathspecs.
const BACKEND_SHARED = ['backend/conftest.py', 'backend/uv.lock', 'backend/pyproject.toml', 'backend/.python-version'];
const BACKEND_APP = ['backend/app', 'backend/db', 'backend/tests', ...BACKEND_SHARED];
const BACKEND_EVALUATION = ['backend/evaluation', 'backend/data', ...BACKEND_SHARED];
const FRONTEND = ['frontend'];

// Each CI job's fast checks; checks in one area run in order, and the two areas run side by side.
const CHECKS = [
  ['backend', [...BACKEND_APP, ...BACKEND_EVALUATION], 'uv run --directory backend ruff check app evaluation tests'],
  ['backend', [...BACKEND_APP, ...BACKEND_EVALUATION], 'uv run --directory backend ruff format --check app evaluation tests'],
  ['backend', [...BACKEND_APP, ...BACKEND_EVALUATION], 'uv run --directory backend mypy'],
  ['backend', BACKEND_APP, 'uv run --directory backend pytest -q tests --cov=app --cov-fail-under=80'],
  ['backend', BACKEND_EVALUATION, 'uv run --directory backend --extra evaluation pytest -q evaluation/tests --cov=evaluation --cov-fail-under=80'],
  ['frontend', FRONTEND, 'pnpm --dir frontend lint --cache --cache-location node_modules/.cache/eslint/'],
  ['frontend', FRONTEND, 'pnpm --dir frontend typecheck'],
  ['frontend', FRONTEND, 'pnpm --dir frontend format:check --cache'],
  ['frontend', FRONTEND, 'pnpm --dir frontend test'],
].map(([area, paths, command]) => ({ area, paths, command }));

function mergeBase() {
  for (const ref of ['origin/main', 'main']) {
    try {
      return git('merge-base', 'HEAD', ref).trim();
    } catch {}
  }
  return 'HEAD';
}

const base = mergeBase();
const fingerprints = new Map();

// A check's fingerprint covers main's commit and the changes under its CI paths, so editing one area leaves the other's results standing.
function fingerprint(paths) {
  const key = paths.join('\0');
  if (fingerprints.has(key)) return fingerprints.get(key);
  const diff = git('diff', '--binary', '--no-renames', base, '--', ...paths);
  const untracked = git('ls-files', '-z', '--others', '--exclude-standard', '--', ...paths)
    .split('\0')
    .filter(Boolean);
  let result = null;
  if (diff || untracked.length > 0) {
    const hash = createHash('sha256').update(base).update(diff);
    for (const file of untracked) hash.update(file).update(readFileSync(join(root, file)));
    result = hash.digest('hex');
  }
  fingerprints.set(key, result);
  return result;
}

const due = CHECKS.map((check) => ({ ...check, fingerprint: fingerprint(check.paths) })).filter(
  (check) => check.fingerprint,
);
if (due.length === 0) process.exit(0);

// Check results outlive the session that produced them, while fix rounds count per session.
const saved = existsSync(stateFile) ? JSON.parse(readFileSync(stateFile, 'utf8')) : {};
const state = { checks: {}, ...saved };
if (state.session !== input.session_id) Object.assign(state, { session: input.session_id, blocks: 0 });

function run(command) {
  return new Promise((resolve) => {
    const child = spawn(command, { cwd: root, shell: true });
    let output = '';
    child.stdout.on('data', (chunk) => (output += chunk));
    child.stderr.on('data', (chunk) => (output += chunk));
    child.on('close', (code) => {
      const tail = output.trimEnd().split('\n').slice(-OUTPUT_TAIL_LINES).join('\n');
      resolve(code === 0 ? null : `${command}\n${tail}`);
    });
  });
}

async function runArea(checks) {
  for (const check of checks) {
    state.checks[check.command] = { fingerprint: check.fingerprint, failure: await run(check.command) };
  }
}

// An unchanged file set keeps its last results, so a turn with no new edits re-runs nothing.
const stale = due.filter((check) => state.checks[check.command]?.fingerprint !== check.fingerprint);
if (stale.length === 0 && state.blocks === 0) process.exit(0);
await Promise.all(
  ['backend', 'frontend'].map((area) => runArea(stale.filter((check) => check.area === area))),
);

const failures = due.map((check) => state.checks[check.command].failure).filter(Boolean);
const names = failures.map((failure) => failure.split('\n')[0]).join('; ');
let output = {};
let blocks = 0;
// A round counts only when a failing check covers Claude's edits, so a failure left untouched (a TDD red step) goes to the user.
if (failures.length > 0 && !stale.some((check) => state.checks[check.command].failure)) {
  output = {
    systemMessage: `Claude stopped without changing the files the failing checks cover, so the stop hook hands over to you: ${names}`,
  };
} else if (failures.length > 0 && state.blocks < MAX_BLOCKS) {
  blocks = state.blocks + 1;
  const reason = [
    `Stop hook, round ${blocks} of ${MAX_BLOCKS}: these checks fail on the branch's changes.`,
    'Fix the root cause in the code, keeping every check, test and threshold as strict as it is, then finish again.',
    'When the failure is intended (a TDD red step) or not yours to fix, finish again without editing the files those checks cover and say why; the hook then hands over to the user.',
    ...failures,
  ].join('\n\n');
  output = { decision: 'block', reason };
} else if (failures.length > 0) {
  output = {
    systemMessage: `Checks still fail after ${MAX_BLOCKS} fix rounds, so the stop hook hands over to you: ${names}`,
  };
}
writeFileSync(stateFile, JSON.stringify({ ...state, blocks }));
console.log(JSON.stringify(output));
