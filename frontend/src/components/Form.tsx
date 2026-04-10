'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Cloud from '@/assets/Cloud';

interface FormData {
  text: string;
  url: string;
}

export default function Form() {
  const router = useRouter();
  const [inputMethod, setInputMethod] = useState<'text' | 'file' | 'url'>(
    'text'
  );
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

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
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

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    sessionStorage.removeItem('analisis_text');
    sessionStorage.removeItem('analisis_url');
    sessionStorage.removeItem('analisis_source_type');

    if (inputMethod === 'file') {
      if (!selectedFile) {
        alert('Por favor, selecciona un archivo primero.');
        return;
      }
      try {
        const text = await selectedFile.text();
        sessionStorage.setItem('analisis_text', text);
        sessionStorage.setItem('analisis_source_type', 'file');
      } catch (error) {
        console.error('Error al leer el archivo:', error);
        alert('Hubo un error al leer el archivo.');
        return;
      }
    } else if (inputMethod === 'url') {
      if (!formData.url.trim()) {
        alert('Por favor, introduce una URL.');
        return;
      }
      sessionStorage.setItem('analisis_url', formData.url);
      sessionStorage.setItem('analisis_source_type', 'url');
    } else {
      if (!formData.text.trim()) {
        alert('Por favor, introduce un texto.');
        return;
      }
      sessionStorage.setItem('analisis_text', formData.text);
      sessionStorage.setItem('analisis_source_type', 'text');
    }

    router.push('/analisis');
  };

  return (
    <form
      className="mb-10 flex w-full max-w-3xl flex-col items-center justify-center gap-6 rounded-2xl border border-gray-100 bg-white p-5 shadow-2xl shadow-gray-200/50 transition-all md:mb-12 md:p-8"
      onSubmit={handleSubmit}
    >
      <div className="flex w-full max-w-md rounded-xl bg-gray-100/80 p-1.5 backdrop-blur-sm">
        <button
          type="button"
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'text'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          }`}
          onClick={() => setInputMethod('text')}
        >
          Pegar Texto
        </button>
        <button
          type="button"
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'file'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          }`}
          onClick={() => setInputMethod('file')}
        >
          Subir Archivo
        </button>
        <button
          type="button"
          className={`flex w-1/3 items-center justify-center rounded-lg py-2.5 text-sm font-semibold transition-all duration-200 ${
            inputMethod === 'url'
              ? 'bg-white text-primary shadow-sm'
              : 'text-gray-500 hover:bg-gray-200/50 hover:text-gray-700'
          }`}
          onClick={() => setInputMethod('url')}
        >
          Pegar URL
        </button>
      </div>

      <div className="flex w-full flex-col gap-4">
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
              className="min-h-40 w-full resize-y rounded-xl border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-800 transition-all placeholder:text-gray-400 focus:border-primary focus:bg-white focus:ring-4 focus:ring-primary/10 focus:outline-none sm:min-h-50 sm:text-base"
              placeholder="Escribe o pega aquí tu texto (al menos 50 caracteres recomendados)..."
              value={formData.text}
              onChange={handleChange}
            ></textarea>
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
              }`}
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
                onChange={handleFileChange}
              />
            </label>
          </div>
        )}

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
              className="w-full rounded-xl border border-gray-200 bg-gray-50 p-4 text-center text-sm text-gray-800 transition-all placeholder:text-gray-400 focus:border-primary focus:bg-white focus:ring-4 focus:ring-primary/10 focus:outline-none sm:text-base"
              placeholder="https://ejemplo.com/noticia"
              value={formData.url}
              onChange={handleChange}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={
            (inputMethod === 'text' && !formData.text.trim()) ||
            (inputMethod === 'file' && !selectedFile) ||
            (inputMethod === 'url' && !formData.url.trim())
          }
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-base font-bold text-white shadow-lg shadow-primary/30 transition-all hover:bg-primary/90 hover:shadow-primary/40 focus:ring-4 focus:ring-primary/20 focus:outline-none active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 disabled:shadow-none sm:text-lg"
        >
          Analizar Texto
        </button>
      </div>
    </form>
  );
}
