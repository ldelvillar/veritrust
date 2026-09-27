---
description: Evaluate the full multi-agent pipeline (Extractor→Translator→Investigator→Health Expert) against labeled HealthVer data or the hand-written gold set and report accuracy
argument-hint: "[--partition gold|validation|test|train] [--limit N] [--seed N] [--replay-evidence CKPT]"
---

Measure how accurately the VeriTrust multi-agent pipeline labels medical claims,
end-to-end, against ground-truth data. The harness lives at
`backend/ml/evaluate_pipeline.py` (`--help` lists every flag); you run it and
interpret the output. `docs/ml-experiments.md` is the lab notebook of earlier
runs.

PREREQUISITES:

- The provider set by `LLM_PROVIDER` in `backend/.env` must be usable: Ollama
  reachable with the configured models pulled, or the hosted provider's API key
  set. The harness checks this with `ensure_llm_available()` and fails fast.
- This is SLOW: every sample runs several sequential LLM calls plus the evidence
  lookups, so a run takes minutes to hours. Keep `--limit` small unless the user
  asks for a full run.

STEPS:

1. From the repo root, run the harness in the background (a run outlasts the
   shell timeout), forwarding any `$ARGUMENTS`:
   `uv run --directory backend --extra ml python -m ml.evaluate_pipeline $ARGUMENTS`
   When `$ARGUMENTS` names no `--partition`, add `--partition gold`; every other
   flag keeps the harness default. If it fails on a missing
   prerequisite, report exactly which one and stop.
   - It resumes from its checkpoint (`backend/results/eval_pipeline_<partition>.jsonl`
     unless `--checkpoint` names another). If it refuses because the checkpoint
     was written with another configuration, rerun with a new `--checkpoint`
     path; `--fresh` deletes the old checkpoint, which may be the baseline of a
     paired comparison, so pass it only when the user asks.
   - Samples that fail mid-run are logged and left out, and a rerun retries only
     those. Report how many failed.

2. Read the printed report: the header (provider, git commit, partition, models,
   prompt versions and, with `--replay-evidence`, how many searches were
   replayed), the excluded counts (uncertain verdicts as abstentions, "sin
   afirmaciones", "juez caído"), the confusion matrix with `falsa` as the
   positive class, accuracy and coverage over firm verdicts, precision / recall /
   F1, and the misclassified firm verdicts.

3. Summarize for the user:
   - Headline metrics and whether they look healthy for a misinformation tool
     (flag low recall on `falsa` especially — missed false claims are the costly
     error here), with coverage beside accuracy: abstaining trades one for the
     other.
   - Patterns in the misclassifications: are errors concentrated in one direction
     (false→true vs true→false)?
   - Where each error originates, reasoned from its checkpoint row (`extracted`,
     `translated`, `sources_kept`, `stances`, `evidence_coverage`,
     `judge_failures`, raw `evidence`): the Extractor (no or wrong claims), the
     Translator (meaning or polarity lost), retrieval (no sources kept), the
     relevance judge (stances), or the verdict rule in `app/core/verdict.py`. The
     Health Expert's LLM only writes the report, which the harness skips unless
     `--with-explanation`.
   - Judge failures measure the judge model breaking its output schema, not
     pipeline quality; report them separately.
   - How the run compares with the latest comparable run (same partition and
     provider) in the notebook. Production runs Ollama, so numbers from a hosted
     provider don't describe what users see; and prompts were tuned on the gold
     set, so gold results are partly in-sample.

4. If the user wants to act on the results, first read the notebook's "No volver
   a intentar" and "Pendiente con mayor expectativa" sections so you don't
   re-propose a refuted idea. Then propose concrete next steps tied to the
   evidence (e.g. a prompt tweak in `prompts.yaml` for the responsible agent). To
   measure a change, rerun on gold or validation (keep test for a final check)
   with a new `--checkpoint` and `--replay-evidence <baseline checkpoint>`, so
   both arms see the same literature. Make NO code changes unless asked.

Report metrics faithfully. If a run was small or many samples were excluded, say
so and note the result is indicative, not conclusive: at n=100 the standard error
on accuracy is about 5 points.
