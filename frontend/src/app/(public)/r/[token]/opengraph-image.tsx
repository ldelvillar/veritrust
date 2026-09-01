import { ImageResponse } from 'next/og';

import { getVerdictInfo } from '@/components/analysis-result/format';
import { fetchPublicJsonServer } from '@/lib/serverApi';
import type { paths } from '@/types/api';

export const alt = 'Informe de credibilidad de VeriTrust';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

type PublicReport =
  paths['/shared/{token}']['get']['responses']['200']['content']['application/json'];

// Degradado de marca para el caso sin informe (token inválido o backend caído).
const FALLBACK_BAND = 'linear-gradient(135deg,#5a44e8,#432dd7 60%,#3722b8)';

export default async function OpengraphImage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let report: PublicReport | null = null;
  try {
    report = await fetchPublicJsonServer<PublicReport>(`/shared/${token}`);
  } catch {
    report = null;
  }

  const verdict = report ? getVerdictInfo(report.verdict) : null;
  const score = report?.credibility ?? null;
  const background = verdict?.band ?? FALLBACK_BAND;
  const headline = verdict?.text ?? 'Detector de desinformación médica';

  return new ImageResponse(
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        background,
        color: 'white',
        padding: '72px 80px',
        fontFamily: 'sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: -1 }}>
          VeriTrust
        </div>
        <div
          style={{
            marginLeft: 20,
            paddingLeft: 20,
            borderLeft: '2px solid rgba(255,255,255,0.4)',
            fontSize: 23,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.85)',
          }}
        >
          Detector de desinformación médica con IA
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center' }}>
        {score !== null && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              width: 234,
              height: 234,
              borderRadius: 234,
              border: '14px solid rgba(255,255,255,0.9)',
              marginRight: 56,
            }}
          >
            <div style={{ fontSize: 100, fontWeight: 800, lineHeight: 1 }}>
              {score}
            </div>
            <div
              style={{
                fontSize: 26,
                fontWeight: 600,
                color: 'rgba(255,255,255,0.85)',
              }}
            >
              / 100
            </div>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: 4,
              color: 'rgba(255,255,255,0.82)',
            }}
          >
            VEREDICTO
          </div>
          <div
            style={{
              fontSize: 86,
              fontWeight: 800,
              lineHeight: 1.05,
              marginTop: 10,
            }}
          >
            {headline}
          </div>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div
          style={{
            fontSize: 26,
            fontWeight: 600,
            color: 'rgba(255,255,255,0.85)',
          }}
        >
          Verificado afirmación por afirmación, con fuentes citadas
        </div>
        <div style={{ fontSize: 26, fontWeight: 700 }}>veritrust.es</div>
      </div>
    </div>,
    { ...size }
  );
}
