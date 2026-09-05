'use client';

import { useEffect, useId, useRef, useState } from 'react';

import ArrowIcon from '@/assets/Arrow';
import DocumentIcon from '@/assets/Document';
import GlobeIcon from '@/assets/Globe';
import Spinner from '@/assets/Spinner';
import TypeIcon from '@/assets/Type';
import UploadIcon from '@/assets/Upload';
import WarningIcon from '@/assets/Warning';
import PdfViewer from '@/components/PdfViewer';
import { useAnalysisSubmission } from '@/hooks/useAnalysisSubmission';
import type { components, paths } from '@/types/api';

type ClientConfig =
  paths['/config']['get']['responses']['200']['content']['application/json'];

const isPdfFile = (file: File): boolean =>
  file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

const isLikelyUrl = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed || /\s/.test(trimmed)) return false;
  try {
    const { hostname } = new URL(
      trimmed.startsWith('http') ? trimmed : `https://${trimmed}`
    );
    return /\.[a-z]{2,}$/i.test(hostname);
  } catch {
    return false;
  }
};

const EXAMPLE_TEXT_1 =
  'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común y refuerza el sistema inmunitario sin ningún riesgo, según un estudio reciente.';
const EXAMPLE_TEXT_2 =
  'Tomar el sol 20 minutos al día sin protección es suficiente para obtener toda la vitamina D que el cuerpo necesita.';
const EXAMPLE_URL_1 = 'www.20minutos.es/salud/actualidad/estudio-vitamina-c';
const EXAMPLE_URL_2 = 'www.larazon.es/salud/asi-influye-la-vitamina-d';

// '.pdf' -> 'PDF', para las etiquetas de tipos aceptados.
const suffixLabel = (suffix: string): string =>
  suffix.replace('.', '').toUpperCase();

const megabytes = (bytes: number): string =>
  `${Math.round(bytes / (1024 * 1024))} MB`;

export default function AnalysisForm({
  limits,
}: {
  limits: ClientConfig | null;
}) {
  const { submit, submitFile, isLoading, error, setError } =
    useAnalysisSubmission();

  const [inputMethod, setInputMethod] =
    useState<components['schemas']['SourceType']>('text');
  const [formData, setFormData] = useState({ text: '', url: '' });
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(150, Math.max(90, el.scrollHeight))}px`;
  }, [formData.text, inputMethod]);

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const applyFile = (file: File) => {
    if (limits && file.size > limits.max_file_bytes) {
      setError(
        `El archivo es demasiado grande. El tamaño máximo permitido es ${megabytes(limits.max_file_bytes)}.`
      );
      return;
    }
    setError(null);
    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      applyFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      applyFile(e.target.files[0]);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    if (e.key !== 'Enter' || e.nativeEvent.isComposing) return;
    const target = e.target as EventTarget | null;
    const isTextArea = target instanceof HTMLTextAreaElement;
    if (isTextArea && e.shiftKey) return;
    if (inputMethod === 'file') return;
    e.preventDefault();
    e.currentTarget.requestSubmit();
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (inputMethod === 'file') {
      if (!selectedFile) {
        setError('Por favor, selecciona un archivo primero.');
        return;
      }
      // Todos los archivos (PDF/TXT/MD) se suben tal cual: el backend extrae el
      // texto y guarda el binario, igual que antes solo se hacía con los PDF.
      await submitFile(selectedFile);
      return;
    }

    if (inputMethod === 'url') {
      if (!formData.url.trim()) {
        setError('Por favor, introduce una URL.');
        return;
      }
      if (!isLikelyUrl(formData.url)) {
        setError(
          'Introduce un enlace válido, por ejemplo www.medio.es/salud/articulo.'
        );
        return;
      }
      const fullUrl = formData.url.startsWith('http')
        ? formData.url
        : `https://${formData.url}`;
      await submit({ url: fullUrl, source_type: 'url' });
      return;
    }

    if (!formData.text.trim()) {
      setError('Por favor, introduce un texto.');
      return;
    }
    await submit({ text: formData.text, source_type: 'text' });
  };

  const trimmedTextLength = formData.text.trim().length;
  const trimmedUrl = formData.url.trim();
  const isUrlValid = isLikelyUrl(trimmedUrl);
  const showUrlHint = trimmedUrl.length > 0 && !isUrlValid;

  // Sin límites conocidos solo se exige texto no vacío; la API tiene la última palabra.
  const isTextLengthValid =
    trimmedTextLength > 0 &&
    (!limits ||
      (trimmedTextLength >= limits.min_input_text_length &&
        trimmedTextLength <= limits.max_input_text_length));

  const canRun =
    (inputMethod === 'text' && isTextLengthValid) ||
    (inputMethod === 'url' && isUrlValid) ||
    (inputMethod === 'file' && !!selectedFile);

  const tabs = [
    { id: 'text' as const, label: 'Texto', Icon: TypeIcon },
    { id: 'url' as const, label: 'Enlace', Icon: GlobeIcon },
    { id: 'file' as const, label: 'Archivo', Icon: DocumentIcon },
  ];

  // Ids estables para asociar cada pestaña con su panel (semántica de tablist).
  const baseId = useId();
  const tabId = (id: string) => `${baseId}-tab-${id}`;
  const panelId = `${baseId}-panel`;
  const urlHintId = `${baseId}-url-hint`;

  // Navegación con flechas del patrón tablist WAI-ARIA (activación automática).
  const handleTabKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const delta = e.key === 'ArrowRight' ? 1 : -1;
    const index = tabs.findIndex(tab => tab.id === inputMethod);
    const next = tabs[(index + delta + tabs.length) % tabs.length].id;
    setInputMethod(next);
    document.getElementById(tabId(next))?.focus();
  };

  const controls = (
    <>
      <div
        role="tablist"
        aria-label="Método de entrada del contenido"
        className="absolute bottom-3.5 left-3.5 inline-flex gap-0.75 rounded-xl border border-line bg-white p-1 shadow-[0_2px_8px_rgba(12,79,82,.12)]"
      >
        {tabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={tabId(id)}
            aria-selected={inputMethod === id}
            aria-controls={panelId}
            tabIndex={inputMethod === id ? 0 : -1}
            disabled={isLoading}
            onClick={() => setInputMethod(id)}
            onKeyDown={handleTabKeyDown}
            className={`flex items-center gap-1.75 rounded-lg px-3 py-1.75 text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
              inputMethod === id
                ? 'bg-primary-soft text-primary-strong'
                : 'text-muted hover:text-body'
            }`}
          >
            <Icon className="size-3.75" />
            <span>{label}</span>
          </button>
        ))}
      </div>
      <button
        type="submit"
        disabled={isLoading || !canRun}
        className="absolute right-3.5 bottom-3.5 flex size-10 items-center justify-center rounded-lg bg-primary text-white transition-colors hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isLoading ? (
          <Spinner className="size-4.5 animate-spin" />
        ) : (
          <ArrowIcon
            className="size-4.5 rotate-180"
            aria-label="Analizar credibilidad"
          />
        )}
      </button>
    </>
  );

  return (
    <>
      <form
        className="relative w-full max-w-190"
        onSubmit={handleSubmit}
        onKeyDown={handleKeyDown}
      >
        {/* Texto tab */}
        {inputMethod === 'text' && (
          <div role="tabpanel" id={panelId} aria-labelledby={tabId('text')}>
            <label htmlFor="analysis-text" className="sr-only">
              Pega el texto o la afirmación a verificar
            </label>
            <div className="relative rounded-xl border border-line-strong bg-surface-subtle pb-17 transition-all focus-within:border-primary focus-within:bg-white focus-within:shadow-[0_0_0_4px_var(--color-primary-soft)]">
              <textarea
                id="analysis-text"
                name="text"
                ref={textareaRef}
                disabled={isLoading}
                className="max-h-37.5 min-h-22.5 w-full resize-none overflow-auto border-0 bg-transparent p-4 font-[inherit] text-base leading-relaxed font-medium text-body placeholder:text-faint focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                placeholder="Ej.: «Beber agua con limón en ayunas elimina las toxinas y previene el cáncer.»"
                value={formData.text}
                onChange={handleChange}
              />
              {controls}
            </div>
          </div>
        )}

        {/* Enlace tab */}
        {inputMethod === 'url' && (
          <div role="tabpanel" id={panelId} aria-labelledby={tabId('url')}>
            <label htmlFor="analysis-url" className="sr-only">
              Introduce la URL del artículo
            </label>
            <div className="relative rounded-xl border border-line-strong bg-surface-subtle pb-17 transition-all focus-within:border-primary focus-within:bg-white focus-within:shadow-[0_0_0_4px_var(--color-primary-soft)]">
              <div className="flex items-center py-5">
                <span className="pr-1 pl-4 text-sm font-bold text-muted">
                  https://
                </span>
                <input
                  id="analysis-url"
                  name="url"
                  type="text"
                  disabled={isLoading}
                  className="flex-1 border-none bg-transparent py-1.5 pr-4 pl-1 font-[inherit] text-base text-body placeholder:text-faint focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                  placeholder="www.medio.es/salud/articulo-a-verificar"
                  value={formData.url}
                  onChange={handleChange}
                  aria-invalid={showUrlHint}
                  aria-describedby={showUrlHint ? urlHintId : undefined}
                />
              </div>
              {showUrlHint && (
                <p
                  id={urlHintId}
                  className="px-4 pb-2 text-xs font-semibold text-faint"
                >
                  Escribe un dominio completo, p. ej. medio.es
                </p>
              )}
              {controls}
            </div>
          </div>
        )}

        {/* Archivo tab */}
        {inputMethod === 'file' && (
          <div role="tabpanel" id={panelId} aria-labelledby={tabId('file')}>
            <div className="relative pb-17">
              <label
                htmlFor="file-upload"
                className={`flex min-h-45 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-6 text-center transition-all ${
                  isDragging
                    ? 'border-primary bg-surface'
                    : 'border-line-strong bg-surface-subtle hover:border-primary hover:bg-surface'
                } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <div className="mb-3 grid size-13 place-items-center rounded-2xl bg-primary-soft text-primary">
                  <UploadIcon className="size-5.5" />
                </div>
                {selectedFile ? (
                  <p className="text-base font-semibold text-ink">
                    <span className="text-primary">{selectedFile.name}</span> ·
                    listo para analizar
                  </p>
                ) : (
                  <p className="text-base font-semibold text-ink">
                    Arrastra un archivo aquí o{' '}
                    <span className="text-primary">búscalo</span>
                  </p>
                )}
                <p className="mt-1.5 text-sm text-muted">
                  Documentos PDF o texto plano (.txt o .md).
                </p>
                <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                  {(limits?.allowed_file_suffixes ?? [])
                    .map(suffixLabel)
                    .map(t => (
                      <span
                        key={t}
                        className="rounded-lg border border-line bg-white px-2.5 py-1 text-2xs font-bold tracking-wide text-muted"
                      >
                        {t}
                      </span>
                    ))}
                  {limits && (
                    <span className="text-2xs font-bold text-faint">
                      máx. {megabytes(limits.max_file_bytes)}
                    </span>
                  )}
                </div>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept={limits?.allowed_file_suffixes.join(',')}
                  disabled={isLoading}
                  onChange={handleFileChange}
                />
              </label>
              {controls}
            </div>

            {selectedFile && isPdfFile(selectedFile) && (
              <div className="mt-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-bold text-body">
                  <DocumentIcon className="size-3.75 text-muted" />
                  Vista previa del PDF
                </div>
                <PdfViewer file={selectedFile} />
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            role="alert"
            className="mt-4 flex w-full items-center gap-2 rounded-xl border border-danger/20 bg-danger-soft p-4 text-sm text-danger-ink"
          >
            <WarningIcon className="size-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}
      </form>

      {inputMethod === 'text' && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs font-bold text-faint">Prueba:</span>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, text: EXAMPLE_TEXT_1 })}
            className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-primary-strong"
          >
            Vitamina C y resfriado
          </button>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, text: EXAMPLE_TEXT_2 })}
            className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-primary-strong"
          >
            Sol y vitamina D
          </button>
        </div>
      )}

      {inputMethod === 'url' && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs font-bold text-faint">Sugerencias:</span>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, url: EXAMPLE_URL_1 })}
            className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-primary-strong"
          >
            20minutos.es
          </button>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, url: EXAMPLE_URL_2 })}
            className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-primary-strong"
          >
            larazon.es
          </button>
        </div>
      )}
    </>
  );
}
