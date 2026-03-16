'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface FormData {
  text: string;
}

export default function Form() {
  const router = useRouter();
  const [formData, setFormData] = useState<FormData>({
    text: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    sessionStorage.setItem('analisis_text', formData.text);
    router.push('/analisis');
  };

  return (
    <form
      className="mb-10 flex w-full max-w-3xl flex-col items-center justify-center gap-4 rounded-lg border border-border bg-white p-4 sm:mb-12 sm:gap-5 sm:p-6 md:p-8"
      onSubmit={handleSubmit}
    >
      <label
        htmlFor="text"
        className="text-center text-lg font-medium text-gray-700 sm:text-xl"
      >
        Introduce el texto de la noticia
      </label>
      <textarea
        name="text"
        id="text"
        className="min-h-40 w-full rounded-lg border border-border p-3 text-sm placeholder:text-gray-400 focus:outline-primary sm:min-h-44 sm:text-base"
        placeholder="Introduce al menos 50 caracteres para un análisis preciso..."
        value={formData.text}
        onChange={handleChange}
      ></textarea>

      <button
        type="submit"
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary/90 focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-400 disabled:hover:bg-gray-400 sm:mt-3 sm:text-base"
      >
        Analizar
      </button>
    </form>
  );
}
