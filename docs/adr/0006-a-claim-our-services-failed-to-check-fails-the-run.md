---
status: accepted
---

# A Claim our services failed to check fails the Run

ADR-0003 made a Claim uncertain when "its Sources or the judge fail", so an Analysis whose judge calls ran out of retries ended done as Dudoso. It used an Allowance unit, counted toward the Dudoso share, and nothing on it said the literature had never been consulted. The judge was the only agent that swallowed its provider's failures, and its parallel calls, up to 8 per Run, are the ones most likely to exceed Mistral's per-second limit. Now a Claim that one of our services failed to check fails the Run with CONNECTION, so no unit is used and Retry stays available. That covers a judge call still failing after the client's retries (a 429, a 5xx or no connection) and a searched Claim whose literature sources all failed. A Dudoso now always comes from the literature, never from our outage.

A judge answer that does not give one Stance per Source still leaves its Claim uncertain, since it is the model's answer rather than an outage. That Claim no longer counts toward Evidence coverage, because what the literature says of it is unknown. Claims left out by the cap of 8 or without a usable query stay uncertain as ADR-0003 says. This amends ADR-0003's rule for failures.

## Considered Options

- **Keep the Verdict and record the failures on the row**: rejected. The user still gets a Dudoso and is charged for it, and the Dudoso share still mixes outages with thin literature.
- **Fail the Run only when every Claim failed**: rejected. A burst of judge calls against the rate limit usually fails some of them, which would still end as a silent Dudoso.
- **Also fail on an unusable judge answer**: rejected. The judge already asks again with half the Sources, and a text whose Claim reliably trips the model would never get a Verdict.

## Consequences

- The MCP Evidence search has no Verdict, so it still returns a Claim whose sources all failed, marked as such. A judge provider failure fails that search too, without using a unit.
- An evaluation sample whose recorded searches leave a Claim without sources now fails on every replay, so the harness leaves it out.
