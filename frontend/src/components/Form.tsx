'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';

import Cloud from '@/assets/Cloud';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import type { components } from '@/types/api';
import { ApiError, fetchJsonWithAuth } from '@/lib/apiClient';
import { ERROR_INTERNAL } from '@/messages';
import type { paths } from '@/types/api';

type CreateAnalysisResponse =
  paths['/analysis']['post']['responses']['200']['content']['application/json'];

interface FormData {
  text: string;
  url: string;
}

const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB — early sanity check before reading
const MAX_TEXT_CHARS = 10_000; // matches backend StringConstraints max_length

export default function Form() {
  const router = useRouter();
  const { getToken } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [inputMethod, setInputMethod] =
    useState<components['schemas']['SourceType']>('url');
  const [formData, setFormData] = useState<FormData>({
    text: '',
    url: '',
  });
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
      setError('El archivo es demasiado grande. El tamaño máximo permitido es 10 MB.');
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
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    if (e.key !== 'Enter' || e.nativeEvent.isComposing) {
      return;
    }

    const target = e.target as EventTarget | null;
    const isTextArea = target instanceof HTMLTextAreaElement;

    if (isTextArea && e.shiftKey) {
      return;
    }

    if (inputMethod === 'file') {
      return;
    }

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

    const requestBody =
      inputMethod === 'url'
        ? { url: formData.url, source_type: 'url' as const }
        : { text: textContent, source_type: finalSourceType };

    setIsLoading(true);

    try {
      const data = await fetchJsonWithAuth<CreateAnalysisResponse>(
        getToken,
        '/analysis',
        {
          method: 'POST',
          body: requestBody,
        }
      );

      if (data.analysis_id) {
        router.push(`/analisis/${data.analysis_id}`);
      } else {
        throw new Error('No se generó un ID de análisis válido.');
      }
    } catch (err) {
      if (err instanceof ApiError && err.code) {
        setError(err.message);
      } else {
        setError(ERROR_INTERNAL);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form
      className="mb-10 flex w-full max-w-3xl flex-col items-center justify-center gap-6 rounded-2xl border border-gray-100 bg-white p-5 shadow-2xl shadow-gray-200/50 transition-all md:mb-12 md:p-8"
      onSubmit={handleSubmit}
      onKeyDown={handleKeyDown}
    >
      <div className="flex w-full max-w-md rounded-xl bg-gray-100/80 p-1.5 backdrop-blur-sm">
        <button
          type="button"
          disabled={isLoading}
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'url'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          } ${isLoading ? 'cursor-not-allowed opacity-50' : ''}`}
          onClick={() => setInputMethod('url')}
        >
          Pegar URL
        </button>
        <button
          type="button"
          disabled={isLoading}
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'file'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          } ${isLoading ? 'cursor-not-allowed opacity-50' : ''}`}
          onClick={() => setInputMethod('file')}
        >
          Subir Archivo
        </button>
        <button
          type="button"
          disabled={isLoading}
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'text'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          } ${isLoading ? 'cursor-not-allowed opacity-50' : ''}`}
          onClick={() => setInputMethod('text')}
        >
          Pegar Texto
        </button>
      </div>

      <div className="flex w-full flex-col gap-4">
        {inputMethod === 'url' && (
          <div className="flex flex-col gap-3">
            <label
              htmlFor="url"
              className="text-center text-lg font-semibold text-gray-800 md:text-xl"
            >
              Introduce una URL
            </label>
            <input
              type="url"
              name="url"
              id="url"
              disabled={isLoading}
              className="w-full rounded-xl border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-800 transition-all placeholder:text-gray-400 focus:border-primary focus:bg-white focus:ring-4 focus:ring-primary/10 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 sm:text-base"
              placeholder="https://ejemplo.com/noticia"
              value={formData.url}
              onChange={handleChange}
            />
          </div>
        )}

        {inputMethod === 'file' && (
          <div className="flex flex-col gap-3">
            <label
              htmlFor="file-upload"
              className="text-center text-lg font-semibold text-gray-800 md:text-xl"
            >
              Selecciona un archivo
            </label>
            <label
              htmlFor="file-upload"
              className={`group flex min-h-40 w-full cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-all sm:min-h-50 ${
                isDragging
                  ? 'scale-[1.01] border-primary bg-primary/5'
                  : 'border-gray-300 bg-gray-50 hover:border-primary/50 hover:bg-gray-100/80'
              } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Cloud
                  className={`mb-4 size-10 transition-colors ${
                    isDragging
                      ? 'text-primary'
                      : 'text-gray-400 group-hover:text-primary/70'
                  }`}
                />
                <p className="mb-2 text-center text-sm text-gray-600">
                  <span className="font-semibold text-primary">
                    Haz clic para subir
                  </span>{' '}
                  o arrastra y suelta el archivo aquí
                </p>
                {selectedFile ? (
                  <div className="mt-2 rounded-lg bg-primary/10 px-4 py-2 text-sm font-semibold text-primary">
                    {selectedFile.name}
                  </div>
                ) : (
                  <p className="mt-1 text-xs font-medium tracking-wider text-gray-400 uppercase">
                    TXT o MD (Máx. 10MB)
                  </p>
                )}
              </div>
              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".txt,.md"
                disabled={isLoading}
                onChange={handleFileChange}
              />
            </label>
          </div>
        )}

        {inputMethod === 'text' && (
          <div className="flex flex-col gap-3">
            <label
              htmlFor="text"
              className="text-center text-lg font-semibold text-gray-800 md:text-xl"
            >
              Introduce el texto
            </label>
            <textarea
              name="text"
              id="text"
              disabled={isLoading}
              className="min-h-40 w-full resize-y rounded-xl border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-800 transition-all placeholder:text-gray-400 focus:border-primary focus:bg-white focus:ring-4 focus:ring-primary/10 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60 sm:min-h-50 sm:text-base"
              placeholder="Escribe o pega aquí tu texto (al menos 50 caracteres recomendados)..."
              value={formData.text}
              onChange={handleChange}
            ></textarea>
          </div>
        )}

        {error && (
          <div className="mt-2 flex w-full items-center gap-2 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
            <WarningIcon className="size-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={
            isLoading ||
            (inputMethod === 'text' && !formData.text.trim()) ||
            (inputMethod === 'file' && !selectedFile) ||
            (inputMethod === 'url' && !formData.url.trim())
          }
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-base font-bold text-white shadow-lg shadow-primary/30 transition-all hover:bg-primary/90 hover:shadow-primary/40 focus:ring-4 focus:ring-primary/20 focus:outline-none active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 disabled:shadow-none sm:text-lg"
        >
          {isLoading ? (
            <>
              <Spinner className="size-5 animate-spin text-white" />
              <span>Analizando...</span>
            </>
          ) : (
            'Analizar Texto'
          )}
        </button>
      </div>
    </form>
  );
}
