// Stop hook: runs CI's fast checks on the areas the branch changed and keeps Claude working while they fail.
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
  execFileSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 1 << 28 });

function mergeBase() {
  for (const ref of ['origin/main', 'main']) {
    try {
      return git('merge-base', 'HEAD', ref).trim();
    } catch {}
  }
  return 'HEAD';
}

const base = mergeBase();
const untracked = git('ls-files', '--others', '--exclude-standard', '--', 'backend', 'frontend')
  .split('\n')
  .filter(Boolean);
const changed = [
  ...git('diff', '--name-only', base, '--', 'backend', 'frontend').split('\n').filter(Boolean),
  ...untracked,
].filter((file) => !file.endsWith('.md'));

// The same areas as CI's path filters, so the hook runs what CI would run.
const touches = (pattern) => changed.some((file) => pattern.test(file));
const backendShared = /^backend\/(conftest\.py|uv\.lock|pyproject\.toml|\.python-version)$/;
const areas = {
  backend: touches(/^backend\//),
  backendApp: touches(/^backend\/(app|db|tests)\//) || touches(backendShared),
  backendEvaluation: touches(/^backend\/(evaluation|data)\//) || touches(backendShared),
  frontend: touches(/^frontend\//),
};

const groups = [
  [
    areas.backend && 'uv run --directory backend ruff check app evaluation tests',
    areas.backend && 'uv run --directory backend ruff format --check app evaluation tests',
    areas.backend && 'uv run --directory backend mypy',
    areas.backendApp &&
      'uv run --directory backend pytest -q tests --cov=app --cov-fail-under=80',
    areas.backendEvaluation &&
      'uv run --directory backend --extra evaluation pytest -q evaluation/tests --cov=evaluation --cov-fail-under=80',
  ],
  [
    areas.frontend && 'pnpm --dir frontend lint',
    areas.frontend && 'pnpm --dir frontend typecheck',
    areas.frontend && 'pnpm --dir frontend format:check',
    areas.frontend && 'pnpm --dir frontend test',
  ],
].map((group) => group.filter(Boolean));

if (groups.every((group) => group.length === 0)) process.exit(0);

const hash = createHash('sha256').update(git('diff', '--binary', base, '--', 'backend', 'frontend'));
for (const file of untracked) hash.update(file).update(readFileSync(join(root, file)));
const fingerprint = hash.digest('hex');

const saved = existsSync(stateFile) ? JSON.parse(readFileSync(stateFile, 'utf8')) : {};
const state = saved.session === input.session_id ? saved : { session: input.session_id, blocks: 0 };
const save = (fields) => writeFileSync(stateFile, JSON.stringify({ ...state, ...fields }));

function block(failures, blocks) {
  save({ fingerprint, failures, blocks, result: 'failed' });
  const reason = [
    `Stop hook, round ${blocks} of ${MAX_BLOCKS}: these checks fail on the branch's changes.`,
    'Fix the root cause in the code, keeping every check, test and threshold as strict as it is, then finish again.',
    ...failures,
  ].join('\n\n');
  console.log(JSON.stringify({ decision: 'block', reason }));
  process.exit(0);
}

function handOver(failures) {
  save({ fingerprint, failures, blocks: 0, result: 'handed-over' });
  const names = failures.map((failure) => failure.split('\n')[0]).join('; ');
  console.log(
    JSON.stringify({
      systemMessage: `Checks still fail after ${MAX_BLOCKS} fix rounds, so the stop hook hands over to you: ${names}`,
    }),
  );
  process.exit(0);
}

function settle(failures) {
  if (failures.length === 0) {
    save({ fingerprint, failures: [], blocks: 0, result: 'passed' });
    process.exit(0);
  }
  if (state.blocks >= MAX_BLOCKS) handOver(failures);
  block(failures, state.blocks + 1);
}

// An unchanged tree keeps its last result, so a turn with no new edits re-runs nothing.
if (state.fingerprint === fingerprint) {
  if (state.result === 'failed') settle(state.failures);
  process.exit(0);
}

function run(command) {
  return new Promise((resolve) => {
    const child = spawn(command, { cwd: root, shell: true });
    let output = '';
    child.stdout.on('data', (chunk) => (output += chunk));
    child.stderr.on('data', (chunk) => (output += chunk));
    child.on('close', (code) => resolve({ command, code, output }));
  });
}

async function runGroup(commands) {
  const results = [];
  for (const command of commands) results.push(await run(command));
  return results;
}

const results = (await Promise.all(groups.map(runGroup))).flat();
const failures = results
  .filter((result) => result.code !== 0)
  .map(
    ({ command, output }) =>
      `${command}\n${output.trimEnd().split('\n').slice(-OUTPUT_TAIL_LINES).join('\n')}`,
  );
settle(failures);
