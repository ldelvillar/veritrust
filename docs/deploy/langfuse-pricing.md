# Langfuse model pricing

Langfuse computes a generation's cost by matching its `model` against a price table.
Mistral's models aren't in Langfuse's built-in table, so VeriTrust's generations show token
counts but no cost until a model definition exists. This is a one-off setting in the
Langfuse project, not code.

Every generation already carries what Langfuse needs: `model` (for example
`mistral-small-latest`) and token usage under the `input` and `output` keys. Generations are
named after their agent (`extractor`, `translator`, `judge`, `health_expert`).

## Add a model definition

1. In the Langfuse project, open **Settings → Models → Add model definition**. Or open any
   trace, click the model badge on a generation and choose **Create Model**, which prefills
   the name and usage types.
2. Fill in:

   | Field          | Value                                 |
   | -------------- | ------------------------------------- |
   | Model name     | `mistral-small-latest`                |
   | Match pattern  | `(?i)^(mistral-small-latest)$`        |
   | `input` price  | input price per 1M tokens ÷ 1,000,000  |
   | `output` price | output price per 1M tokens ÷ 1,000,000 |

   Prices are **per token**, and the usage type names must be exactly `input` and `output`.
3. Take the prices from [Mistral's pricing page](https://mistral.ai/pricing). In November
   2026, `mistral-small-latest` (Mistral Small 4) is listed at about $0.15 per 1M input and
   $0.60 per 1M output tokens, which is `0.00000015` and `0.0000006` per token. Check the
   page before entering them, because the alias moves to newer models.
4. Save, then run one analysis and check that its generations show a cost.

## Things to know

- **Not retroactive.** A definition prices only generations ingested after it is saved;
  older traces keep no cost.
- **One definition per model.** If `MISTRAL_*_MODEL` points an agent at another model, add a
  definition for that name too. The Groq judge rotation and the other hosted providers are
  development-only, so they only need one if you want dev costs.
- **Self-hosted Ollama** has no per-token bill. Leave it unpriced, or price it at an
  estimated GPU cost per token if you want comparable numbers.
- **When Mistral changes prices**, edit the definition. Past generations keep the cost they
  were ingested with.
