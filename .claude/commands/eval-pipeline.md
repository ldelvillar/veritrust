---
description: Evaluate the full multi-agent pipeline (Extractor→Translator→Investigator→Health Expert) against labeled PubHealth data and report accuracy
argument-hint: "[--limit N] [--partition train|test|validation] [--seed N]"
---

Measure how accurately the VeriTrust multi-agent pipeline labels medical claims,
end-to-end, against ground-truth data. The harness lives at
`backend/ml/evaluation/evaluate_pipeline.py`; you run it and interpret the output.

PREREQUISITES (check, don't assume):
- Ollama must be reachable with the pipeline models pulled (`llama3`, `llama3.2`,
  `translategemma`). The script calls `ensure_ollama_available()` and will fail
  fast if not.
- The BERT classifier must exist under `backend/models/bert_classifier`.
- The ml extra must be installed (`uv sync --frozen --extra ml`).
- This is SLOW: each sample runs 3 sequential Ollama calls + BERT. Default
  `--limit` is 30; keep it small unless the user asks for a full run.

STEPS:

1. From `backend/`, run the harness, forwarding any `$ARGUMENTS`:
   `uv run --extra ml python -m ml.evaluation.evaluate_pipeline $ARGUMENTS`
   If `$ARGUMENTS` is empty it evaluates 30 balanced samples from the validation
   split. If it fails on a missing prereq, report exactly which one and stop —
   do not silently skip the run.

2. Read the printed report: confusion matrix (TP/TN/FP/FN, with `falsa` as the
   positive class), accuracy / precision / recall / F1, the count of samples
   skipped as "sin afirmaciones" (no medical claims detected), and the list of
   misclassified examples.

3. Summarize for the user:
   - Headline metrics and whether they look healthy for a misinformation tool
     (flag low recall on `falsa` especially — missed false claims are the costly
     error here).
   - Patterns in the misclassifications: are errors concentrated in one direction
     (false→true vs true→false)? Do skipped "no claims" samples suggest the
     Extractor is dropping valid medical text?
   - Whether the failure looks like it originates in the Extractor (no claims),
     the Translator, or the Health Expert/BERT verdict — reason from the evidence,
     don't guess.

4. If the user wants to act on the results, propose concrete next steps tied to
   the evidence (e.g. a prompt tweak in `prompts.yaml` for the responsible agent,
   then re-run this command to compare) — but make NO code changes unless asked.

Report metrics faithfully. If a run was small or skipped samples were high, say
so and note the result is indicative, not conclusive.
