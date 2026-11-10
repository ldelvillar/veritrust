'use client';

import type { ReactNode } from 'react';

import CheckIcon from '@/assets/Check';
import ClipboardIcon from '@/assets/Clipboard';
import McpIcon from '@/assets/Mcp';
import Button from '@/components/Button';
import { clientEnv } from '@/env/client';
import { COPY_LABEL, useCopyToClipboard } from '@/hooks/useCopyToClipboard';
import { usePlan } from '@/hooks/usePlan';

const TOOLS = [
  {
    name: 'verify_claim',
    description:
      'Verifica un texto o un enlace y devuelve el veredicto, las afirmaciones y las fuentes.',
  },
  {
    name: 'get_verification',
    description:
      'Recupera el resultado de una verificación que sigue en curso.',
  },
  {
    name: 'search_evidence',
    description:
      'Busca la evidencia de las afirmaciones de un texto, sin emitir veredicto.',
  },
  {
    name: 'get_evidence',
    description: 'Recupera el resultado de una búsqueda de evidencia en curso.',
  },
];

const CODE_CLASS =
  'rounded-md border border-line bg-surface-subtle px-1.5 py-0.5 font-mono text-xs break-all text-ink';

function buildClients(
  serverUrl: string
): { name: string; steps: ReactNode[] }[] {
  return [
    {
      name: 'Claude (web y escritorio)',
      steps: [
        <>
          Abre <strong>Personalizar → Conectores</strong>, pulsa{' '}
          <strong>+ Añadir</strong> y elige{' '}
          <strong>Añadir conector personalizado</strong>.
        </>,
        <>
          Escribe el nombre «VeriTrust», pega la dirección del servidor y
          confirma.
        </>,
        <>
          Inicia sesión con tu cuenta de VeriTrust cuando se te pida. Después,
          activa el conector en cada chat desde el botón <strong>+</strong> →{' '}
          <strong>Conectores</strong>.
        </>,
      ],
    },
    {
      name: 'ChatGPT',
      steps: [
        <>
          En <strong>Plugins</strong>, pulsa <strong>+</strong> y elige{' '}
          <strong>Añadir servidor MCP personalizado</strong>. Según tu plan de
          ChatGPT puede que esta opción no esté disponible.
        </>,
        <>
          Pega la dirección del servidor como <em>Server URL</em> y elige la
          autenticación <strong>OAuth</strong>.
        </>,
        <>
          Crea el plugin, instálalo e inicia sesión con tu cuenta de VeriTrust.
        </>,
      ],
    },
    {
      name: 'Claude Code',
      steps: [
        <>
          Ejecuta{' '}
          <code
            className={CODE_CLASS}
          >{`claude mcp add --transport http veritrust ${serverUrl}`}</code>
        </>,
        <>
          Dentro de Claude Code, escribe{' '}
          <code className={CODE_CLASS}>/mcp</code>, elige VeriTrust e inicia
          sesión con tu cuenta en el navegador.
        </>,
      ],
    },
  ];
}

export default function McpCard() {
  const { limits } = usePlan();
  const { state: copyState, copy } = useCopyToClipboard();

  if (!limits) return null;

  const serverUrl = `${clientEnv.apiUrl}/mcp`;

  return (
    <section
      id="mcp"
      aria-labelledby="cuenta-mcp-title"
      className="scroll-mt-6 rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)] md:p-7"
    >
      <div className="flex items-start gap-3.5">
        <span
          aria-hidden
          className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary"
        >
          <McpIcon className="size-5" />
        </span>
        <div className="min-w-0">
          <h2
            id="cuenta-mcp-title"
            className="text-lg font-bold tracking-tight text-ink"
          >
            Conecta tu asistente de IA
          </h2>
          <p className="mt-1 text-sm font-medium text-muted">
            Verifica afirmaciones médicas desde Claude, ChatGPT o Claude Code
            sin salir de la conversación.
          </p>
        </div>
      </div>

      {limits.mcp ? (
        <>
          <div className="mt-6 border-t border-line pt-6">
            <p className="text-sm font-bold text-ink">Dirección del servidor</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <code className="min-w-50 flex-1 rounded-xl border border-line bg-surface-subtle px-3.5 py-2.5 font-mono text-sm break-all text-ink">
                {serverUrl}
              </code>
              <Button variant="ghost" onClick={() => void copy(serverUrl)}>
                {copyState === 'copied' ? (
                  <CheckIcon className="size-4" aria-hidden />
                ) : (
                  <ClipboardIcon className="size-4" aria-hidden />
                )}
                <span aria-live="polite">{COPY_LABEL[copyState]}</span>
              </Button>
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-2.5">
            {buildClients(serverUrl).map(client => (
              <details
                key={client.name}
                className="group rounded-xl border border-line bg-surface-subtle px-4 py-3"
              >
                <summary className="cursor-pointer text-sm font-bold text-ink">
                  {client.name}
                </summary>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm font-medium text-body marker:font-bold marker:text-primary">
                  {client.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
              </details>
            ))}
          </div>

          <div className="mt-6 border-t border-line pt-6">
            <p className="text-sm font-bold text-ink">
              Herramientas que ofrece
            </p>
            <dl className="mt-3 grid gap-3">
              {TOOLS.map(tool => (
                <div key={tool.name}>
                  <dt>
                    <code className={CODE_CLASS}>{tool.name}</code>
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-muted">
                    {tool.description}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 text-xs font-medium text-muted">
              Cada verificación o búsqueda de evidencia cuenta como un análisis
              de tu cuota mensual, y las verificaciones aparecen en tu
              historial.
            </p>
          </div>
        </>
      ) : (
        <p className="mt-5 rounded-xl bg-surface-subtle px-3.5 py-3 text-sm font-semibold text-muted">
          Conectar tu asistente es una función del plan Pro.{' '}
          <a href="#plan" className="text-primary underline underline-offset-2">
            Ver el plan Pro
          </a>
        </p>
      )}
    </section>
  );
}
