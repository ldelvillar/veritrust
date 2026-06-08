'use client';

import { useState } from 'react';

import DocumentIcon from '@/assets/Document';
import GlobeIcon from '@/assets/Globe';
import ShieldIcon from '@/assets/Shield';
import Spinner from '@/assets/Spinner';
import TypeIcon from '@/assets/Type';
import UploadIcon from '@/assets/Upload';
import WarningIcon from '@/assets/Warning';
import PdfViewer from '@/components/PdfViewer';
import { useAnalysisSubmission } from '@/hooks/useAnalysisSubmission';
import type { components } from '@/types/api';

const isPdfFile = (file: File): boolean =>
  file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

const EXAMPLE_TEXT_1 =
  'El consumo diario de vitamina C en dosis altas previene por completo el resfriado común y refuerza el sistema inmunitario sin ningún riesgo, según un estudio reciente.';
const EXAMPLE_TEXT_2 =
  'Tomar el sol 20 minutos al día sin protección es suficiente para obtener toda la vitamina D que el cuerpo necesita.';

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_TEXT_CHARS = 10_000;

export default function AnalysisForm() {
  const { submit, submitPdf, isLoading, error, setError } =
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

    let textContent = '';
    const finalSourceType: components['schemas']['SourceType'] = inputMethod;

    if (inputMethod === 'file') {
      if (!selectedFile) {
        setError('Por favor, selecciona un archivo primero.');
        return;
      }
      // Los PDF se suben tal cual, el backend extrae el texto y guarda el binario.
      if (isPdfFile(selectedFile)) {
        await submitPdf(selectedFile);
        return;
      }
      try {
        textContent = await selectedFile.text();
      } catch (err) {
        console.error('Error al leer el archivo:', err);
        setError('Hubo un error al leer el archivo.');
        return;
      }
      if (textContent.length > MAX_TEXT_CHARS) {
        setError(
          `El archivo supera el límite de ${MAX_TEXT_CHARS.toLocaleString()} caracteres. Por favor, acorta el texto.`
        );
        return;
      }
    } else if (inputMethod === 'url') {
      if (!formData.url.trim()) {
        setError('Por favor, introduce una URL.');
        return;
      }
    } else {
      if (!formData.text.trim()) {
        setError('Por favor, introduce un texto.');
        return;
      }
      textContent = formData.text;
    }

    const fullUrl = formData.url.startsWith('http')
      ? formData.url
      : `https://${formData.url}`;
    const requestBody =
      inputMethod === 'url'
        ? { url: fullUrl, source_type: 'url' as const }
        : { text: textContent, source_type: finalSourceType };

    await submit(requestBody);
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

  return (
    <form
      className="w-full max-w-4xl rounded-2xl border border-[#e8e6f4] bg-white p-7 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]"
      onSubmit={handleSubmit}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className="mb-5">
        <h2 className="text-[20px] font-bold tracking-tight text-[#15162c]">
          Nuevo análisis
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-[#7e7f99]">
          Elige cómo quieres aportar el contenido a verificar. Procesamos texto,
          páginas web y documentos.
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-5 flex gap-2 rounded-2xl border border-[#e8e6f4] bg-[#f4f2fd] p-1.5">
        {tabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            disabled={isLoading}
            onClick={() => setInputMethod(id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-xl px-3.5 py-3 text-[14.5px] font-bold transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
              inputMethod === id
                ? 'bg-white text-primary shadow-[0_1px_2px_rgba(20,22,44,.04),0_4px_14px_rgba(92,80,200,.05)]'
                : 'text-[#7e7f99] hover:text-[#33344c]'
            }`}
          >
            <Icon className="size-4.5" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Texto tab */}
      {inputMethod === 'text' && (
        <div>
          <div className="mb-2.5 flex items-center gap-2 text-[13px] font-bold text-[#33344c]">
            <TypeIcon className="size-3.75 text-[#7e7f99]" />
            Pega el texto o la afirmación a verificar
          </div>
          <textarea
            name="text"
            disabled={isLoading}
            className="min-h-47 w-full resize-y rounded-xl border border-[#dcd9ee] bg-[#faf9fe] p-4 font-[inherit] text-[15px] leading-relaxed text-[#33344c] transition-all placeholder:text-[#a3a4ba] focus:border-primary focus:bg-white focus:shadow-[0_0_0_4px_rgba(99,86,230,.12)] focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            placeholder="Ej.: «Beber agua con limón en ayunas elimina las toxinas y previene el cáncer.»"
            value={formData.text}
            onChange={handleChange}
          />
          <div className="mt-2.5 flex items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[12.5px] font-bold text-[#a3a4ba]">
                Probar un ejemplo:
              </span>
              <button
                type="button"
                onClick={() =>
                  setFormData({ ...formData, text: EXAMPLE_TEXT_1 })
                }
                className="rounded-full border border-[#e8e6f4] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#33344c] transition-all hover:border-primary hover:bg-[#f4f2fd] hover:text-primary"
              >
                Vitamina C y resfriado
              </button>
              <button
                type="button"
                onClick={() =>
                  setFormData({ ...formData, text: EXAMPLE_TEXT_2 })
                }
                className="rounded-full border border-[#e8e6f4] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#33344c] transition-all hover:border-primary hover:bg-[#f4f2fd] hover:text-primary"
              >
                Sol y vitamina D
              </button>
            </div>
            <span className="shrink-0 text-[12.5px] font-semibold text-[#a3a4ba]">
              {formData.text.length} caracteres
            </span>
          </div>
        </div>
      )}

      {/* Enlace tab */}
      {inputMethod === 'url' && (
        <div>
          <div className="mb-2.5 flex items-center gap-2 text-[13px] font-bold text-[#33344c]">
            <GlobeIcon className="size-3.75 text-[#7e7f99]" />
            Introduce la URL del artículo
          </div>
          <div className="flex overflow-hidden rounded-xl border border-[#dcd9ee] bg-[#faf9fe] transition-all focus-within:border-primary focus-within:bg-white focus-within:shadow-[0_0_0_4px_rgba(99,86,230,.12)]">
            <span className="flex items-center self-stretch border-r border-[#e8e6f4] bg-white px-3.5 text-[14px] font-bold text-[#7e7f99]">
              https://
            </span>
            <input
              name="url"
              type="text"
              disabled={isLoading}
              className="flex-1 border-none bg-transparent px-4 py-3.5 font-[inherit] text-[15px] text-[#33344c] placeholder:text-[#a3a4ba] focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
              placeholder="www.medio.es/salud/articulo-a-verificar"
              value={formData.url}
              onChange={handleChange}
            />
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <span className="text-[12.5px] font-bold text-[#a3a4ba]">
              Sugerencias:
            </span>
            <button
              type="button"
              onClick={() =>
                setFormData({
                  ...formData,
                  url: 'www.20minutos.es/salud/actualidad/estudio-vitamina-c',
                })
              }
              className="rounded-full border border-[#e8e6f4] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#33344c] transition-all hover:border-primary hover:bg-[#f4f2fd] hover:text-primary"
            >
              20minutos.es
            </button>
            <button
              type="button"
              onClick={() =>
                setFormData({
                  ...formData,
                  url: 'www.larazon.es/salud/asi-influye-la-vitamina-d',
                })
              }
              className="rounded-full border border-[#e8e6f4] bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#33344c] transition-all hover:border-primary hover:bg-[#f4f2fd] hover:text-primary"
            >
              larazon.es
            </button>
          </div>
        </div>
      )}

      {/* Archivo tab */}
      {inputMethod === 'file' && (
        <div>
          <div className="mb-2.5 flex items-center gap-2 text-[13px] font-bold text-[#33344c]">
            <DocumentIcon className="size-3.75 text-[#7e7f99]" />
            Sube un documento para analizar
          </div>
          <label
            htmlFor="file-upload"
            className={`flex min-h-45 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-8 text-center transition-all ${
              isDragging
                ? 'border-primary bg-[#f4f2fd]'
                : 'border-[#dcd9ee] bg-[#faf9fe] hover:border-primary hover:bg-[#f4f2fd]'
            } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="mb-4 grid size-15 place-items-center rounded-2xl bg-[#efedfc] text-primary">
              <UploadIcon className="size-6.5" />
            </div>
            {selectedFile ? (
              <p className="text-[16px] font-semibold text-[#15162c]">
                <span className="text-primary">{selectedFile.name}</span> ·
                listo para analizar
              </p>
            ) : (
              <p className="text-[16px] font-semibold text-[#15162c]">
                Arrastra un archivo aquí o{' '}
                <span className="text-primary">búscalo</span>
              </p>
            )}
            <p className="mt-1.5 text-[13px] text-[#7e7f99]">
              Documentos PDF o texto plano (.txt o .md).
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
              {['PDF', 'TXT', 'MD'].map(t => (
                <span
                  key={t}
                  className="rounded-lg border border-[#e8e6f4] bg-white px-2.5 py-1 text-[11.5px] font-bold tracking-wide text-[#7e7f99]"
                >
                  {t}
                </span>
              ))}
              <span className="text-[11.5px] font-bold text-[#a3a4ba]">
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

          {selectedFile && isPdfFile(selectedFile) && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-2 text-[13px] font-bold text-[#33344c]">
                <DocumentIcon className="size-3.75 text-[#7e7f99]" />
                Vista previa del PDF
              </div>
              <PdfViewer file={selectedFile} />
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 flex w-full items-center gap-2 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
          <WarningIcon className="size-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 flex items-center gap-4 border-t border-[#e8e6f4] pt-5">
        <div className="flex items-center gap-2 text-[12.5px] leading-snug text-[#7e7f99]">
          <ShieldIcon className="size-3.75 shrink-0 text-[#a3a4ba]" />
          <span>
            El contenido se procesa de forma privada y no se usa para entrenar
            modelos. Las afirmaciones pueden contrastarse con literatura
            biomédica pública (Europe PMC).
          </span>
        </div>
        <div className="flex-1" />
        <button
          type="submit"
          disabled={isLoading || !canRun}
          className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-7 py-3.5 text-[15.5px] font-semibold text-white shadow-[0_8px_20px_rgba(99,86,230,.32)] transition-all hover:-translate-y-px hover:shadow-[0_12px_26px_rgba(99,86,230,.4)] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {isLoading ? (
            <>
              <Spinner className="size-5 animate-spin" />
              <span>Analizando...</span>
            </>
          ) : (
            <span>Analizar credibilidad</span>
          )}
        </button>
      </div>
    </form>
  );
}
