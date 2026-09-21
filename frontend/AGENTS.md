# Frontend

Next.js (App Router). Run every command from the **repo root** — never `cd` into this directory.

## Commands

```bash
pnpm --dir frontend install                  # Install deps
pnpm --dir frontend dev                      # Dev server (http://localhost:3000)
pnpm --dir frontend build                    # Production build (also type-checks)
pnpm --dir frontend lint                     # ESLint
pnpm --dir frontend format:check             # Prettier (CI gates on this; `prettier --write .` to fix)
pnpm --dir frontend generate:api-types       # Regenerate src/types/api.d.ts from OpenAPI (backend must be running)
```

## Conventions

- **`src/types/api.d.ts`** — Generated from the backend's OpenAPI spec; never edit by hand.
- **SVG icons** — icon components live in `frontend/src/assets/` as default exports (`SVGProps<SVGSVGElement>` spread, `stroke="currentColor"`); import and size them via `className`. Don't define inline icon functions in feature files; add or reuse an asset instead.
- **Color tokens & headers** — neutrals come from the semantic `@theme` tokens in `src/styles/globals.css` (`text-ink`/`body`/`muted`/`faint`, `border-line`/`line-strong`, `bg-surface`/`surface-subtle`) plus the brand `accent`/`primary`; never reintroduce `slate-*`/`gray-*` or hardcoded hex greys, nor inline `style={{ color }}`. Page titles use the shared `<PageHeader>` (`src/components/PageHeader.tsx`). System/UI failure states (fetch errors, form validation, destructive actions) use the `--color-danger`/`-soft`/`-ink`/`-g1`/`-g2` tokens (`bg-danger`, `text-danger-ink`, …) — deliberately a different hue from `--color-verdict-fake`, which is reserved for an actual "false" verdict. Likewise, UI success confirmations (e.g. a submitted form) use `--color-success`/`-soft`/`-ink`, distinct from `--color-verdict-real`. The brand teal lives in `--color-primary`/`-strong`/`-soft`/`-soft-strong` and `--color-accent`, dark brand sections in `--color-ink-deep`; use those tokens rather than arbitrary `[#…]` values. The only literal hex left are the verdict band gradients in `analysis-result/format.ts` and the fallback in `r/[token]/opengraph-image.tsx`, which render through `next/og` and cannot resolve CSS custom properties.
- **Tamaños de fuente y radios** — usar siempre las utilidades de la escala (`text-2xs` a `text-5xl`, `text-display-*` para titulares en serif, `rounded-xs` a `rounded-3xl`). No introducir valores arbitrarios del tipo `text-[15px]` o `rounded-[18px]`. Si un diseño parece pedir un valor intermedio, la respuesta correcta es elegir el tramo más cercano, no crear uno nuevo.
- **Verdict vocabulary** — the three verdict states are always "Verdadero"/"Falso"/"Dudoso", sourced from `VERDICT_LABEL` in `frontend/src/components/analysis-result/format.ts`; never hardcode alternate wording (e.g. "Fiable", "Engañoso") in a new screen.
