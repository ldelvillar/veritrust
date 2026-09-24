# VeriTrust

VeriTrust checks medical text, web pages and documents for misinformation by grounding each medical claim in the biomedical literature and reporting a verdict with its evidence.

## Analysis lifecycle

**Analysis**:
One submission of medical content (text, URL or file) by a user, together with its outcome.
_Avoid_: job, check, request, news item

**Analysis lifecycle**:
The sequence of statuses an Analysis moves through: it starts **pending**, ends **done** or **failed**, and returns to **pending** only through a Retry or a Reanalyze.
_Avoid_: workflow, state machine

**Pending**:
The status of an Analysis whose outcome is not known yet; the content is being prepared or is moving through the pipeline.
_Avoid_: running, in progress, queued

**Done**:
The status of an Analysis that produced a verdict with its report.
_Avoid_: completed, finished, succeeded

**Failed**:
The status of an Analysis that ended without a verdict, carrying the reason as an error code; finding no medical claims is a failure.
_Avoid_: error, crashed

**Stage**:
The step of the pipeline a pending Analysis is currently in: preparing, extractor, translator, investigator or health expert.
_Avoid_: step, phase

**Run**:
One pass of the pipeline over a pending Analysis, from preparing its content to its verdict or failure; Retry and Reanalyze each start a new Run.
_Avoid_: attempt, execution, job

**Retry**:
Returning a failed Analysis to pending to run it again on the same content.
_Avoid_: rerun, resubmit

**Reanalyze**:
Returning a done Analysis to pending to run it again on the same content, discarding its previous verdict.
_Avoid_: rerun, refresh, retry

**Orphaned analysis**:
A pending Analysis that has outlived the time limit with no work queued or running for it, and is therefore failed.
_Avoid_: stale, stuck, zombie

**Origin**:
Where an Analysis was submitted from: the web app or an MCP client.
_Avoid_: channel, source (a source is a piece of literature)
