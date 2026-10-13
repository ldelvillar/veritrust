# Pipeline experiment log

A log of what has been tried, negative results included, so dead ends are not repeated.
This README summarises the current state; the dated entries, one file per month, keep
the reasoning. A new entry goes at the end of the current month's file and, if it
changes the state, is reflected here. Entries are written in English from October 2026;
earlier months stay in Spanish. Label strings the harness prints and stores (`verdadera`,
`falsa`, `incierta`, `parcialmente falsa`, «sin afirmaciones», «juez caído») are kept
as-is.

Since August 2026 the dataset is HealthVer, the clean measure is the gold set
`data/gold_es.jsonl` via `evaluation/evaluate_pipeline.py --partition gold`, and **the
BERT classifier is no longer part of the pipeline** (see «Retirada del clasificador BERT»
in [2026-08.md](2026-08.md)). Since 2026-10-12 the harness lives in `evaluation/`;
earlier entries cite `ml/`, its path at the time.

## How to measure

Each checkpoint row stores in `evidence` the raw results of every search.
`--replay-evidence <ckpt>` serves those searches from the recording, failed ones
included, and only queries live the ones it cannot find:

```bash
uv run --directory backend --extra evaluation python -m evaluation.evaluate_pipeline --partition gold --limit 100 --checkpoint results/base.jsonl
uv run --directory backend --extra evaluation python -m evaluation.evaluate_pipeline --partition gold --limit 100 --checkpoint results/variante.jsonl --replay-evidence results/base.jsonl
```

- **Changes to the judge or the verdict rule**: the extractor and translator run at
  temperature 0, so the queries repeat and almost all the Evidence is replayed.
- **Changes to the extractor or translator**: the queries change and those searches go
  live. The report line `Evidencia : N/M búsquedas reproducidas` says how many were
  replayed; if few were, the comparison is not paired on Evidence.
- **It does not pin the judge**: with the Evidence frozen, the variation left between
  runs is the LLM's own, which is part of what is being measured.

Checkpoints from before 2026-09-22 store no raw Evidence and cannot serve as a baseline.

To compare **only the judge**, `evaluation.evaluate_judge` re-judges the Claims and
candidate Sources of a pipeline checkpoint, without extractor or translator: it only
loads the judge model. It takes the single-Claim samples (with several, the row does not
say which searches belong to which) and picks provider and model from the environment,
like the pipeline:

```bash
OLLAMA_JUDGE_MODEL=gemma4:12b uv run --directory backend --extra evaluation python -m evaluation.evaluate_judge --cases results/base.jsonl --checkpoint results/judge_gemma4.jsonl
```

`--minutes N` stops starting new cases after that time; the run resumes later.

## Do not retry

- **Tuning the claim-only classifier** (another base model, more epochs, more margin
  tuning): four architectures converge at ~87–89%. The ceiling comes from the task
  (classifying truthfulness without Evidence learns style, not truth), not the
  architecture. Details in [2026-07-bert-pubhealth.md](2026-07-bert-pubhealth.md).
- **Folding `mixture` into `falsa`**, or any relabelling that contaminates a class.
- **Retraining BERT on HealthVer and putting it back in the pipeline**: two independent
  paired tests (p = 0.0127 and p = 0.0013) say it is redundant, and on its own it scores
  42.31% against 60.6% for a constant predictor. The ceiling is the task's, not the
  training's. Since 2026-09-01 the code is no longer in the tree: it would first have to
  be recovered from `a95e318`, which is friction in the right direction.
- **Removing the translator**: it did not only feed the classifier. `investigator.py`
  stops retrieval if `translated_statements` is empty; without the translator there is
  no Evidence and without Evidence there is no Verdict.
- **Treating absence of Evidence as falsehood**: it scores well on a set full of
  well-known hoaxes and produces "fever is false". Any rule that rewards the
  literature's silence is measuring PubMed's coverage, not truthfulness.
- **Pushing the judge towards `contradicts` by prompt**: v4 achieved it and the split was
  4 right and 4 wrong (p = 0.42). On a Claim the literature does not address, more
  decisiveness is more chance, not more signal. See the 2026-09-01 section in
  [2026-09.md](2026-09.md).
- **Judging one Source per call**: with `llama3.2` it is more decisive, but calls more
  false Claims `verdadera` (25 against 22 of 95 on the same Evidence) and costs one call
  per Source. See the 2026-09-30 section in [2026-09.md](2026-09.md).
- **`llama3` (8B) as judge**: more decisive in the same wrong direction; 30 of 33 firm
  false Claims come out `verdadera`. A bigger model from the same family is not the way
  out.
- **Reasoning fields before `stances`**: `claim_analysis` sinks `contradicts` on false
  Claims from 85 to 51 and breaks verdadera→falsa = 0. Stating the thesis in the positive
  primes topical matching. With `mistral-small`, the judge labels better without a
  preamble.
- **Growing the gold set with more hand-written hoaxes**: ~15 of every 100 fall into the
  coverage blind spot and would only repeat the same ceiling with slightly narrower
  error bars (SE 4.7 → 3.3 when doubling n). If more rows are written, make them a
  **held-out** set: extractor v4, judge v3 and translator v3 were tuned looking at this
  set, so the 71 is partly in-sample.

## Next steps

Reordered after the v6 and v7 runs of 2026-09-01, which exhausted the judge as a lever
through prompting and through scaffolding:

1. **Retrieval coverage for popular-science hoaxes** — the largest bucket and the only
   one left with a clear mechanism: ~15/100 Claims with no Stance at all because PubMed
   and Europe PMC do not index refutations of popular beliefs (carrots and myopia, wet
   hair and colds, 10% of the brain). It needs a source that does cover them — Cochrane
   plain language summaries, MedlinePlus, NHS Health A–Z — not a prompt. It is
   architecture work, not text work.

   Risk to declare before picking a source: a _fact-checking_ API (Google Fact Check
   Tools, used in `ml/evaluation/evaluate_factcheck.py` until it was deleted) indexes
   exactly the **well-known** hoaxes the gold set is made of. Pointing one at the other
   inflates accuracy for a reason that does not transfer to new misinformation; it is
   the same kind of error as PubHealth's style separability. If that route is taken, the
   held-out set must exist before measuring it.

2. **Judge model capacity** — resolved in code: on false Claims, `llama3.2` gives
   1.3–1.7 `supports` per `contradicts` and `llama3` (8B) 6.0, and the 2026-10-01
   screening ([2026-10.md](2026-10.md)) gives 0.05 with `ministral-3:14b` on Ollama,
   which is now the default judge (`ollama_judge_model`). Deployment remains: it needs a
   16 GB GPU and a redone memory budget (see [docs/deploy/ops.md](../deploy/ops.md)).
3. **Held-out set of ~50 rows** — not for precision, but to measure how much of the 71
   transfers out of sample. Written once, stored, and looked at only once. A
   prerequisite for point 1 if the chosen source is a _fact-checking_ one.

## No longer levers

The decision band and threshold (flat sweep within noise at n=100), the judge prompt with
`mistral-small` (v4, p = 0.42; with `llama3.2` it is a lever, see 2026-09-25 in
[2026-09.md](2026-09.md)), the judge's generation order (v7, p = 0.052 against) and
growing the gold set with more hoaxes of the same kind.

## Known ceiling

With the current sources, ~15 of the gold set's 50 false Claims are not verifiable, so
the reachable maximum is around 85/100, not 100.

## Index

[2026-07-bert-pubhealth.md](2026-07-bert-pubhealth.md) — BERT classifier on PubHealth,
closed era:

- Improvement history: 3 classes, no lowercasing, the real learning rate → 87.9% firm
- 2026-07-14 Base-model bake-off — BioBERT won
- 2026-07-14 Renormalising fake_prob — partial improvement
- 2026-07-15 Blending fake_prob with the Evidence's Stance — neutral
- 2026-07-15 Sweep of the global verdict band — the current band is already optimal
- 2026-07-15 «Sin afirmaciones» is domain filtering, not an extractor failure
- 2026-07-15 Medical-only sampling — an honest baseline, and it is worse
- 2026-07-15 Diagnosis: BioBERT reads register, not content

[2026-08.md](2026-08.md):

- 2026-08-30 Dataset replaced: PubHealth → HealthVer
- 2026-08-31 Hand-written gold set
- 2026-08-30/31 Prompts: judge v3 (polarity) and extractor v4 (scope)
- 2026-08-31 BERT classifier removed — two paired tests
- 2026-08-31 Absence of Evidence is not proof of falsehood
- 2026-08-31 Diagnosis: the bottleneck is the judge, not retrieval
- 2026-08-31 Threshold at the neutral point — correct, but no longer buys anything
- 2026-08-31 The translator was correcting the misinformation — translator v3

[2026-09.md](2026-09.md):

- 2026-09-01 Judge v4: forcing the judge to commit — rejected
- 2026-09-01 Reasoning before labelling (`claim_analysis`) — rejected
- 2026-09-01 BERT code deleted
- 2026-09-22 Recorded Evidence for paired comparisons
- 2026-09-25 Judge v5 and translator v4: prompt-injection markers — adopted
- 2026-09-30 Judge v6 with one field per Source; extractor and translator v5 — adopted

[2026-10.md](2026-10.md):

- 2026-10-01 Judge-only screening — Ministral 14B, local candidate
- 2026-10-12 Analysis Verdict from Claim Verdicts: `parcialmente falsa` — adopted
