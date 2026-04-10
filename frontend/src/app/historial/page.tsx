'use client';

import { useAuth } from '@clerk/nextjs';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Magnifier from '@/assets/Magnifier';
import Spinner from '@/assets/Spinner';
import { CONFIG } from '@/config';

interface HistoryItem {
  id: string;
  user_id: string;
  source_type: 'text' | 'file' | 'url';
  input_text: string | null;
  input_url: string | null;
  label: string;
  confidence: number | string;
  explanation: string;
  created_at: string;
}

const getTitle = (item: HistoryItem): string => {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
};

const getSource = (item: HistoryItem): string => {
  if (item.source_type === 'file') return 'Carga de archivo';
  if (item.source_type === 'text') return 'Texto pegado';

  if (!item.input_url) return 'Enlace';

  try {
    return new URL(item.input_url).hostname;
  } catch {
    return 'Enlace';
  }
};

const getTypeLabel = (sourceType: HistoryItem['source_type']): string => {
  if (sourceType === 'file') return 'Archivo';
  if (sourceType === 'url') return 'Enlace';
  return 'Texto';
};

const getScore = (confidence: number | string): number => {
  const parsed = Number(confidence);
  if (Number.isNaN(parsed)) return 0;

  const normalized = parsed <= 1 ? parsed * 100 : parsed;
  return Math.max(0, Math.min(100, Math.round(normalized)));
};

const getScoreColor = (score: number): string => {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
};

export default function HistorialPage() {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    document.title = 'Historial de Análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.'
      );
  }, []);

  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);

      try {
        const URL = CONFIG.API_URL + '/historial';
        const token = await getToken();

        if (!token) {
          throw new Error('No se pudo obtener el token de autenticación.');
        }

        const response = await fetch(URL, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            typeof errorData.detail === 'string'
              ? errorData.detail
              : Array.isArray(errorData.detail)
                ? errorData.detail[0].msg
                : `Status ${response.status}: Error al conectar con el servidor`;
          throw new Error(errorMessage);
        }

        const data = await response.json();
        const items = Array.isArray(data.items) ? data.items : [];
        setHistory(items);
        setTotalCount(
          typeof data.count === 'number' ? data.count : items.length
        );
      } catch (error) {
        console.error('Error al obtener el historial de análisis:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [getToken]);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Análisis anteriores
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Revisa y gestiona tus informes previos de credibilidad de noticias.
          </p>
        </div>

        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-primary/8 px-4 py-2 text-sm font-bold text-primary"
        >
          <span aria-hidden>↓</span>
          Exportar todo
        </button>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
        <label className="relative block">
          <Magnifier className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            readOnly
            placeholder="Buscar artículos por título o palabra clave"
            className="h-11 w-full rounded-xl border border-border bg-white pl-10 text-sm text-slate-500 outline-none"
          />
        </label>

        <button
          type="button"
          className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
        >
          Todos los tipos
        </button>

        <button
          type="button"
          className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
        >
          Rango de fechas
        </button>

        <button
          type="button"
          className="h-11 rounded-xl border border-border bg-white px-4 text-sm font-semibold text-slate-600"
        >
          Puntuación: mayor a menor
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-sm">
        <div className="grid grid-cols-[2.2fr_0.8fr_0.9fr_1.2fr_0.9fr] gap-4 border-b border-border bg-slate-50 px-5 py-4 text-xs font-bold tracking-widest text-slate-400 uppercase">
          <span>Título del artículo</span>
          <span>Tipo</span>
          <span>Fecha de análisis</span>
          <span>Puntuación de credibilidad</span>
          <span className="text-right">Acción</span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center gap-3 px-5 py-12 text-sm font-semibold text-slate-500">
            <Spinner className="size-5 animate-spin text-primary" />
            Cargando análisis...
          </div>
        ) : history.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm font-medium text-slate-500">
            Aún no tienes análisis.
          </div>
        ) : (
          <ul>
            {history.map(item => {
              const score = getScore(item.confidence);
              const scoreColor = getScoreColor(score);

              return (
                <li
                  key={item.id}
                  className="grid grid-cols-[2.2fr_0.8fr_0.9fr_1.2fr_0.9fr] items-center gap-4 border-b border-border px-5 py-4 last:border-b-0"
                >
                  <div className="min-w-0">
                    <p className="truncate text-base font-bold text-slate-800">
                      {getTitle(item)}
                    </p>
                    <p className="mt-1 truncate text-xs font-semibold text-slate-400">
                      Fuente: {getSource(item)}
                    </p>
                  </div>

                  <span className="text-sm font-semibold text-slate-600">
                    {getTypeLabel(item.source_type)}
                  </span>

                  <span className="text-sm font-semibold text-slate-500">
                    {new Date(item.created_at).toLocaleString('es-ES', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>

                  <div className="flex items-center gap-3">
                    <div className="h-2 w-full max-w-24 rounded-full bg-slate-200">
                      <div
                        className={`h-full rounded-full ${scoreColor}`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                    <span className="text-sm font-black text-slate-700">
                      {score}/100
                    </span>
                  </div>

                  <Link
                    href={`/analisis/${item.id}`}
                    className="justify-self-end text-sm font-bold text-primary"
                  >
                    Ver informe →
                  </Link>
                </li>
              );
            })}
          </ul>
        )}

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border bg-slate-50 px-5 py-3">
          <p className="text-xs font-semibold text-slate-400">
            {isLoading
              ? 'Cargando registros...'
              : `Mostrando ${history.length === 0 ? 0 : 1} a ${history.length} de ${totalCount} registros`}
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-400"
            >
              ‹
            </button>
            <button
              type="button"
              className="size-8 rounded-lg bg-primary text-sm font-bold text-white"
            >
              1
            </button>
            <button
              type="button"
              className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500"
            >
              2
            </button>
            <button
              type="button"
              className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-500"
            >
              3
            </button>
            <button
              type="button"
              className="size-8 rounded-lg border border-border bg-white text-sm font-bold text-slate-400"
            >
              ›
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
