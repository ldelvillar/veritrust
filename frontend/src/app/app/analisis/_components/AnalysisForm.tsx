'use client';

import { useId, useState } from 'react';

import DocumentIcon from '@/assets/Document';
import GlobeIcon from '@/assets/Globe';
import Spinner from '@/assets/Spinner';
import TypeIcon from '@/assets/Type';
import UploadIcon from '@/assets/Upload';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import PdfViewer from '@/components/PdfViewer';
import { useAnalysisSubmission } from '@/hooks/useAnalysisSubmission';
import type { components } from '@/types/api';

const isPdfFile = (file: File): boolean =>
  file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

const EXAMPLE_TEXT_1 =
  'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común y refuerza el sistema inmunitario sin ningún riesgo, según un estudio reciente.';
const EXAMPLE_TEXT_2 =
  'Tomar el sol 20 minutos al día sin protección es suficiente para obtener toda la vitamina D que el cuerpo necesita.';
const EXAMPLE_URL_1 = 'www.20minutos.es/salud/actualidad/estudio-vitamina-c';
const EXAMPLE_URL_2 = 'www.larazon.es/salud/asi-influye-la-vitamina-d';

const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function AnalysisForm() {
  const { submit, submitFile, isLoading, error, setError } =
    useAnalysisSubmission();

  const [inputMethod, setInputMethod] =
    useState<components['schemas']['SourceType']>('text');
  const [formData, setFormData] = useState({ text: '', url: '' });
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const applyFile = (file: File) => {
    if (file.size > MAX_FILE_BYTES) {
      setError(
        'El archivo es demasiado grande. El tamaño máximo permitido es 10 MB.'
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

  const canRun =
    (inputMethod === 'text' && formData.text.trim().length > 10) ||
    (inputMethod === 'url' && formData.url.trim().length > 4) ||
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

  return (
    <form
      className="relative w-full max-w-190 overflow-hidden rounded-[22px] border-2 border-[#e7e3fb] bg-white shadow-[0_0_0_1px_rgba(67,45,215,.05),0_20px_54px_rgba(83,69,216,.16)]"
      onSubmit={handleSubmit}
      onKeyDown={handleKeyDown}
    >
      {/* Band */}
      <div className="flex flex-col gap-3 border-b border-[#e7e3fb] bg-[linear-gradient(120deg,#efedfc,#f7f5ff)] px-4 py-3.5 sm:flex-row sm:items-center sm:px-5.5">
        <span className="text-sm font-extrabold tracking-tight text-[#3722b8]">
          Contenido a verificar
        </span>
        <div
          role="tablist"
          aria-label="Método de entrada del contenido"
          className="flex gap-0.75 rounded-[11px] border border-line bg-white p-1 sm:ml-auto sm:inline-flex"
        >
          {tabs.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={tabId(id)}
              aria-selected={inputMethod === id}
              aria-controls={panelId}
              disabled={isLoading}
              onClick={() => setInputMethod(id)}
              className={`flex flex-1 items-center justify-center gap-1.75 rounded-lg px-3 py-1.75 text-[13px] font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none ${
                inputMethod === id
                  ? 'bg-[#efedfc] text-[#3722b8]'
                  : 'text-muted hover:text-body'
              }`}
            >
              <Icon className="size-3.75" />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 sm:p-5.5">
        {/* Texto tab */}
        {inputMethod === 'text' && (
          <div
            role="tabpanel"
            id={panelId}
            aria-labelledby={tabId('text')}
            className="flex min-h-50 flex-col justify-center"
          >
            <label htmlFor="analysis-text" className="sr-only">
              Pega el texto o la afirmación a verificar
            </label>
            <textarea
              id="analysis-text"
              name="text"
              disabled={isLoading}
              className="min-h-37.5 w-full resize-y rounded-[14px] border border-line-strong bg-surface-subtle p-4 font-[inherit] text-[15.5px] leading-relaxed font-medium text-body transition-all placeholder:text-faint focus:border-primary focus:bg-white focus:shadow-[0_0_0_4px_#efedfc] focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
              placeholder="Ej.: «Beber agua con limón en ayunas elimina las toxinas y previene el cáncer.»"
              value={formData.text}
              onChange={handleChange}
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[12.5px] font-bold text-faint">
                  Prueba:
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, text: EXAMPLE_TEXT_1 })
                  }
                  className="rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-[#3722b8]"
                >
                  Vitamina C y resfriado
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, text: EXAMPLE_TEXT_2 })
                  }
                  className="rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-[#3722b8]"
                >
                  Sol y vitamina D
                </button>
              </div>
              <span className="shrink-0 text-[12.5px] font-semibold text-faint">
                {formData.text.length} caracteres
              </span>
            </div>
          </div>
        )}

        {/* Enlace tab */}
        {inputMethod === 'url' && (
          <div
            role="tabpanel"
            id={panelId}
            aria-labelledby={tabId('url')}
            className="flex min-h-50 flex-col justify-center"
          >
            <label htmlFor="analysis-url" className="sr-only">
              Introduce la URL del artículo
            </label>
            <div className="flex overflow-hidden rounded-[14px] border border-line-strong bg-surface-subtle transition-all focus-within:border-primary focus-within:bg-white focus-within:shadow-[0_0_0_4px_#efedfc]">
              <span className="flex items-center self-stretch border-r border-line bg-white px-3.5 text-[14px] font-bold text-muted">
                https://
              </span>
              <input
                id="analysis-url"
                name="url"
                type="text"
                disabled={isLoading}
                className="flex-1 border-none bg-transparent px-4 py-3.5 font-[inherit] text-[15px] text-body placeholder:text-faint focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                placeholder="www.medio.es/salud/articulo-a-verificar"
                value={formData.url}
                onChange={handleChange}
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-[12.5px] font-bold text-faint">
                Sugerencias:
              </span>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, url: EXAMPLE_URL_1 })}
                className="rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-[#3722b8]"
              >
                20minutos.es
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, url: EXAMPLE_URL_2 })}
                className="rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] font-semibold text-body transition-all hover:border-primary hover:bg-surface hover:text-[#3722b8]"
              >
                larazon.es
              </button>
            </div>
          </div>
        )}

        {/* Archivo tab */}
        {inputMethod === 'file' && (
          <div role="tabpanel" id={panelId} aria-labelledby={tabId('file')}>
            <div className="flex min-h-50 flex-col justify-center">
              <label
                htmlFor="file-upload"
                className={`flex min-h-45 w-full cursor-pointer flex-col items-center justify-center rounded-[14px] border-2 border-dashed py-6 text-center transition-all ${
                  isDragging
                    ? 'border-primary bg-surface'
                    : 'border-line-strong bg-surface-subtle hover:border-primary hover:bg-surface'
                } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <div className="mb-3 grid size-13 place-items-center rounded-2xl bg-[#efedfc] text-primary">
                  <UploadIcon className="size-5.5" />
                </div>
                {selectedFile ? (
                  <p className="text-[16px] font-semibold text-ink">
                    <span className="text-primary">{selectedFile.name}</span> ·
                    listo para analizar
                  </p>
                ) : (
                  <p className="text-[16px] font-semibold text-ink">
                    Arrastra un archivo aquí o{' '}
                    <span className="text-primary">búscalo</span>
                  </p>
                )}
                <p className="mt-1.5 text-[13px] text-muted">
                  Documentos PDF o texto plano (.txt o .md).
                </p>
                <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
                  {['PDF', 'TXT', 'MD'].map(t => (
                    <span
                      key={t}
                      className="rounded-lg border border-line bg-white px-2.5 py-1 text-[11.5px] font-bold tracking-wide text-muted"
                    >
                      {t}
                    </span>
                  ))}
                  <span className="text-[11.5px] font-bold text-faint">
                    máx. 10 MB
                  </span>
                </div>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  accept=".txt,.md,.pdf"
                  disabled={isLoading}
                  onChange={handleFileChange}
                />
              </label>
            </div>

            {selectedFile && isPdfFile(selectedFile) && (
              <div className="mt-4">
                <div className="mb-2 flex items-center gap-2 text-[13px] font-bold text-body">
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

        {/* Footer */}
        <div className="mt-4.5 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
          <p className="text-[12.5px] leading-normal font-medium text-muted sm:flex-1">
            El contenido se procesa de forma privada y no se usa para entrenar
            modelos.
          </p>
          <Button
            type="submit"
            size="lg"
            disabled={isLoading || !canRun}
            className="w-full sm:w-auto sm:shrink-0"
          >
            {isLoading ? (
              <>
                <Spinner className="size-5 animate-spin" />
                <span>Analizando...</span>
              </>
            ) : (
              <span>Analizar credibilidad</span>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
